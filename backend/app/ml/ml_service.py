
import os
import torch
import numpy as np
import xgboost as xgb
from app.ml.architectures.unet import RefugeUNet
from app.ml.architectures.gru import GlaucomaProgressionGRU
from sklearn.preprocessing import StandardScaler
from PIL import Image

class MLInferenceService:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.unet = None
        self.gru = None
        self.xgb_model = None
        self.scaler = StandardScaler()
        
        # Load all models into memory immediately upon initialization
        self._load_models()

    def _load_models(self):
        weights_dir = os.path.join(os.path.dirname(__file__), 'weights')
        
        # 1. Load U-Net
        self.unet = RefugeUNet().to(self.device)
        unet_path = os.path.join(weights_dir, 'refuge_unet.pth')
        self.unet.load_state_dict(torch.load(unet_path, map_location=self.device))
        self.unet.eval() # Set to evaluation mode
        
        
        # 2. Initialize and load GRU (using configuration parameters)
        # Assumes input_size = number of clinical features (e.g., 10)
        self.gru_model = GlaucomaProgressionGRU(input_size=5, hidden_size=32, num_layers=1, dropout=0.5).to(self.device)
        gru_path = os.path.join(weights_dir, 'gru_best_overall.pth')
        if os.path.exists(gru_path):
            self.gru_model.load_state_dict(torch.load(gru_path, map_location=self.device))
            self.gru_model.eval()

        # 3. Load XGBoost core booster natively
        self.xgb_model = xgb.Booster()
        xgb_path = os.path.join(weights_dir, 'xgboost_model.json')
        if os.path.exists(xgb_path):
            self.xgb_model.load_model(xgb_path)
    def _preprocess_image(self, image_bytes, target_size=(512, 512)):
        """
        Transforms raw HTTP request bytes into a valid PyTorch inference tensor.
        Replicates val_test_transforms exactly.
        """
        # Load binary byte stream directly into a standard PIL RGB Image
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        
        # Inference pipeline transformation sequence
        transform_pipeline = T.Compose([
            T.Resize(target_size),
            T.ToTensor(),  # Automatically scales pixels from [0, 255] integers to [0.0, 1.0] floats
            # Add T.Normalize if your training script utilized mean/std normalization arrays
        ])
        
        # Apply transformation and insert the explicit batch dimension at index 0 -> [1, 3, 512, 512]
        tensor = transform_pipeline(image).unsqueeze(0)
        return tensor.to(self.device)
    
    def predict_glaucoma_segmentation(self, raw_image_bytes):
        """Izvršava predikciju nad jednom fundus slikom oka."""
        input_tensor = self._preprocess_image(raw_image_bytes)
        
        with torch.no_grad():
            logits = self.unet(input_tensor)
            probabilities = torch.sigmoid(logits)
            
            # Prag 0.5 za binarizaciju maski
            masks = (probabilities > 0.5).int().squeeze(0).cpu().numpy()
            
        # Kanal 0 je Disk, Kanal 1 je Cup (kako je definisano u tvom Datasetu)
        optic_disc_mask = masks[0]
        optic_cup_mask = masks[1]
        
        # Izračunavanje VCDR-a (Vertical Cup-to-Disc Ratio)
        disc_rows = np.any(optic_disc_mask, axis=1)
        cup_rows = np.any(optic_cup_mask, axis=1)
        
        if not np.any(disc_rows) or not np.any(cup_rows):
            vcdr = 0.0
        else:
            disc_diameter = np.max(np.where(disc_rows)) - np.min(np.where(disc_rows)) + 1
            cup_diameter = np.max(np.where(cup_rows)) - np.min(np.where(cup_rows)) + 1
            vcdr = float(cup_diameter / disc_diameter)
        
        return {
            "vcdr": float(vcdr),
            "status": "High Risk / Glaucoma Suspect" if vcdr > 0.65 else "Normal",
            # Clinical frontend clients can utilize raw segmentations via coordinate arrays or compressed PNG files
            "metrics": {
                "disc_pixel_area": int(np.sum(optic_disc_mask)),
                "cup_pixel_area": int(np.sum(optic_cup_mask))
            }
        }

    def _calculate_vcdr(self, disc_mask, cup_mask):
        """Calculates the structural vertical diameter ratio between the cup and disc."""
        # Find all row indexes where pixels are activated
        disc_rows = np.any(disc_mask, axis=1)
        cup_rows = np.any(cup_mask, axis=1)
        
        if not np.any(disc_rows) or not np.any(cup_rows):
            return 0.0
            
        # Vertical diameter calculated as total distance between outer boundaries
        disc_diameter = np.max(np.where(disc_rows)) - np.min(np.where(disc_rows)) + 1
        cup_diameter = np.max(np.where(cup_rows)) - np.min(np.where(cup_rows)) + 1
        
        return cup_diameter / float(disc_diameter)

    def predict_progression(self, sequence_data):
        """
        Input matrix shape from frontend: [Timesteps, 5]
        Internal shapes processed:
          - Scaler: [Timesteps, 5]
          - GRU: [1, Timesteps, 5]
          - XGBoost: [1, Timesteps * 5]
        """
        # 1. Pretvaranje u NumPy niz tipa float32
        raw_sequence = np.array(sequence_data, dtype=np.float32) # [Timesteps, 5]
        timesteps, num_features = raw_sequence.shape

        # 2. Skaliranje identično kao u treningu (StandardScaler)
        # Maskiranje nula ovde nije potrebno jer nam frontend šalje samo stvarne posete pacijenta
        scaled_features = self.scaler.transform(raw_sequence) # [Timesteps, 5]

        # 3. Priprema oblika za GRU -> dodajemo batch dimenziju (1 pacijent)
        gru_input = np.expand_dims(scaled_features, axis=0) # [1, Timesteps, 5]
        gru_input_tensor = torch.tensor(gru_input, dtype=torch.float32).to(self.device)

        # Izvršavanje GRU mreže
        with torch.no_grad():
            gru_logits = self.gru_model(gru_input_tensor).squeeze(-1)
            gru_probability = torch.sigmoid(gru_logits).cpu().numpy()[0] # Vraća float

        # 4. Priprema oblika za XGBoost -> Poravnavamo sve posete u jedan 1D niz
        xgb_input_features = scaled_features.reshape(1, -1) # [1, Timesteps * 5]
        dmatrix_format = xgb.DMatrix(xgb_input_features)
        
        # Izvršavanje XGBoost-a
        xgb_probability = self.xgb_model.predict(dmatrix_format)[0] # Vraća float

        # 5. Ensembler fuzija (40% GRU + 60% XGBoost)
        final_ensemble_probability = (0.4 * gru_probability) + (0.6 * xgb_probability)

        # Izlazni format prilagođen tvom frontend-u
        return {
            "progression_probability": float(final_ensemble_probability),
            "status": "High Progression Risk" if final_ensemble_probability >= 0.5 else "Stable Condition",
            "raw_metrics": {
                "gru_score": float(gru_probability),
                "xgboost_score": float(xgb_probability),
                "total_visits_analyzed": timesteps
            }
        }
    def _preprocess_image(self, image_bytes):
        """Pretvara sirove bajtove iz HTTP zahteva u OpenCV RGB format i primenjuje Albumentations."""
        # 1. Čitamo bajtove preko PIL-a i obavezno prebacujemo u RGB
        pil_image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        
        # 2. Pretvaramo u NumPy niz (OpenCV format koji Albumentations očekuje)
        image_np = np.array(pil_image)
        
        # 3. Primenjujemo Albumentations transformacije
        augmented = self.unet_transforms(image=image_np)
        input_tensor = augmented['image'] # Ovo je već PyTorch tenzor oblika [3, 512, 512]
        
        # 4. Dodajemo batch dimenziju -> [1, 3, 512, 512] i šaljemo na grafičku/procesor
        return input_tensor.unsqueeze(0).to(self.device)
# Instantiate a single global instance of the service
ml_service = MLInferenceService()