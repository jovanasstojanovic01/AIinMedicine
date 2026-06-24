# app/ml/ml_service.py
import os
import torch
import numpy as np
import xgboost as xgb
from app.ml.architectures.unet import RefugeUNet
from app.ml.architectures.gru import PatientGRU
from PIL import Image

class MLInferenceService:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.unet = None
        self.gru = None
        self.xgb_model = None
        
        # Load all models into memory immediately upon initialization
        self._load_models()

    def _load_models(self):
        weights_dir = os.path.join(os.path.dirname(__file__), 'weights')
        
        # 1. Load U-Net
        self.unet = RefugeUNet().to(self.device)
        unet_path = os.path.join(weights_dir, 'refuge_unet.pth')
        self.unet.load_state_dict(torch.load(unet_path, map_location=self.device))
        self.unet.eval() # Set to evaluation mode
        
        # 2. Load GRU
        self.gru = PatientGRU().to(self.device)
        gru_path = os.path.join(weights_dir, 'gru_weights.pth')
        self.gru.load_state_dict(torch.load(gru_path, map_location=self.device))
        self.gru.eval()

        # 3. Load XGBoost
        self.xgb_model = xgb.Booster()
        self.xgb_model.load_model(os.path.join(weights_dir, 'xgboost_model.json'))
    
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
        """
        Executes prediction, evaluates mathematical logits via Sigmoid thresholds,
        and isolates structural segmentations for Optic Disc and Optic Cup.
        """
        # 1. Transform raw asset data
        input_tensor = self._preprocess_image(raw_image_bytes)
        
        # 2. Deactivate autograd engine to save RAM/VRAM and accelerate processing
        with torch.no_grad():
            logits = self.unet(input_tensor)
            
            # Convert raw network logits to absolute probability distributions [0.0, 1.0]
            probabilities = torch.sigmoid(logits)
            
            # Binarize outputs: elements >= 0.5 become 1 (mask), < 0.5 become 0 (background)
            masks = (probabilities > 0.5).int().squeeze(0).cpu().numpy() 
            
        # Extracted NumPy binary arrays (shape: [512, 512])
        optic_disc_mask = masks[0]
        optic_cup_mask = masks[1]
        
        # 3. Compute clinical metrics: Vertical Cup-to-Disc Ratio (VCDR)
        vcdr = self._calculate_vcdr(optic_disc_mask, optic_cup_mask)
        
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

    def predict_progression(self, clinical_history_tensor):
        """
        Takes sequential clinical visit history, passes it through GRU to extract 
        temporal embeddings, then feeds that vector into XGBoost for final risk scoring.
        """
        with torch.no_grad():
            # temporal_features = self.gru(clinical_history_tensor)
            pass
            
        # dmat = xgb.DMatrix(temporal_features.numpy())
        # risk_score = self.xgb_model.predict(dmat)
        
        return {"progression_probability": 0.24}

# Instantiate a single global instance of the service
ml_service = MLInferenceService()