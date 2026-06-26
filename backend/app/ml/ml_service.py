
import os
import torch
import numpy as np
import xgboost as xgb
from app.ml.architectures.unet import RefugeUNet
from app.ml.architectures.gru import GlaucomaProgressionGRU
from sklearn.preprocessing import StandardScaler
from PIL import Image
import io
import torchvision.transforms as T
from flask import current_app

class MLInferenceService:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.unet = None
        self.gru = None
        self.xgb_model = None
        self.scaler = StandardScaler()
        
        
        self._load_models()

    def _load_models(self):
        
        
        self.unet = RefugeUNet().to(self.device)
        unet_path = current_app.config['REFUGEUNET_WEIGHTS']
        self.unet.load_state_dict(torch.load(unet_path, map_location=self.device))
        self.unet.eval() 
        
        
        
        
        self.gru_model = GlaucomaProgressionGRU(input_size=5, hidden_size=32, num_layers=1, dropout=0.5).to(self.device)
        gru_path = current_app.config['GRU_WEIGHTS']
        if os.path.exists(gru_path):
            self.gru_model.load_state_dict(torch.load(gru_path, map_location=self.device))
            self.gru_model.eval()

        
        self.xgb_model = xgb.Booster()
        xgb_path = current_app.config['XGB_MODEL']
        if os.path.exists(xgb_path):
            self.xgb_model.load_model(xgb_path)
    import torchvision.transforms as T

    def _preprocess_image(self, image_bytes, target_size=(current_app.config['CFP_IMAGE_SIZE'], current_app.config['CFP_IMAGE_SIZE'])):
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        
        transform_pipeline = T.Compose([
            T.Resize(target_size),
            T.ToTensor(),  
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]) 
        ])
        
        tensor = transform_pipeline(image).unsqueeze(0)
        return tensor.to(self.device)
    
    def predict_glaucoma_segmentation(self, raw_image_bytes):
        input_tensor = self._preprocess_image(raw_image_bytes)

        with torch.no_grad():
            logits = self.unet(input_tensor)
            probabilities = torch.sigmoid(logits)
            
            masks = (probabilities > 0.5).int().squeeze(0).cpu().numpy()

        pred_disc = masks[0]
        pred_cup = masks[1]

        klinicki_parametri = self.unet.extract_clinical_parameters(pred_disc, pred_cup)
        height, width = pred_disc.shape
        rgb_mask = np.zeros((height, width, 3), dtype=np.uint8)
        rgb_mask[pred_disc == 1] = [255, 0, 0]
        rgb_mask[pred_cup == 1] = [0, 255, 0]

        mask_image = Image.fromarray(rgb_mask)
        buffer = io.BytesIO()
        mask_image.save(buffer, format="PNG")
        mask_bytes = buffer.getvalue()

        return {
            "vcdr": klinicki_parametri["vCDR"],
            "hcdr": klinicki_parametri["hCDR"],
            "acdr": klinicki_parametri["aCDR"],
            "rim_area": klinicki_parametri["rim_area_pixels"],
            "status": klinicki_parametri["diagnosis"],
            "mask_bytes": mask_bytes,
        }

    def predict_progression(self, sequence_data):
        """
        Input matrix shape from frontend: [Timesteps, 5]
        Internal shapes processed:
          - GRU: [1, Timesteps, 5]
          - XGBoost: [1, Timesteps * 5]
        """
        
        raw_sequence = np.array(sequence_data, dtype=np.float32) 
        timesteps, num_features = raw_sequence.shape

        
        
        scaled_features = self.scaler.transform(raw_sequence) 

        
        gru_input = np.expand_dims(scaled_features, axis=0) 
        gru_input_tensor = torch.tensor(gru_input, dtype=torch.float32).to(self.device)

        
        with torch.no_grad():
            gru_logits = self.gru_model(gru_input_tensor).squeeze(-1)
            gru_probability = torch.sigmoid(gru_logits).cpu().numpy()[0] 

        
        xgb_input_features = scaled_features.reshape(1, -1) 
        dmatrix_format = xgb.DMatrix(xgb_input_features)
        
        
        xgb_probability = self.xgb_model.predict(dmatrix_format)[0] 

        
        final_ensemble_probability = (0.4 * gru_probability) + (0.6 * xgb_probability)

        
        return {
            "progression_probability": float(final_ensemble_probability),
            "status": "High Progression Risk" if final_ensemble_probability >= 0.5 else "Stable Condition",
            "raw_metrics": {
                "gru_score": float(gru_probability),
                "xgboost_score": float(xgb_probability),
                "total_visits_analyzed": timesteps
            }
        }
    
        
    
        
        
    
        
        
    
    
        
        
    

ml_service = MLInferenceService()