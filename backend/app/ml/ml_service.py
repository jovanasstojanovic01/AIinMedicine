
import json
import os
import torch
import numpy as np
from app.ml.architectures.unet import RefugeUNet
from app.ml.architectures.gru import GlaucomaVFProgressionGRU
from sklearn.preprocessing import StandardScaler
from PIL import Image
import io
import torchvision.transforms as T
from flask import current_app
import joblib

from app.utils.data_prep import correct_IOP

class MLInferenceService:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.unet = None
        self.gru = None
        self.scaler = joblib.load(current_app.config['SCALER_PATH'])
        
        
        self._load_models()

    def _load_models(self):
        
        
        self.unet = RefugeUNet().to(self.device)
        unet_path = current_app.config['REFUGEUNET_WEIGHTS']
        self.unet.load_state_dict(torch.load(unet_path, map_location=self.device))
        self.unet.eval() 
        
        
        
        
        self.gru_model = GlaucomaVFProgressionGRU(input_size=7, hidden_size=64, num_layers=1, dropout=0.3).to(self.device)
        gru_path = current_app.config['GRU_WEIGHTS']
        if os.path.exists(gru_path):
            self.gru_model.load_state_dict(torch.load(gru_path, map_location=self.device))
            self.gru_model.eval()

        
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

    def predict_next_visit_vf_mean(self, istorija_pregleda, cct_pacijenta, eye="OD"):
            """
            Gradi sekvencu za PyTorch GRU model na osnovu hronološke istorije i
            vraca predviđeni VF_mean za sledeću posetu (t+1).
            """
            if not istorija_pregleda:
                raise ValueError("Pacijent mora imati barem jednu posetu za predikciju.")

            privremene_posete = []
            
            for p in istorija_pregleda:
                
                sirovi_iop = p.od_iop if eye == "OD" else p.os_iop
                
                
                vcdr, hcdr, acdr, rim_area = 0.0, 0.0, 0.0, 0.0
                if p.multimedija:
                    vcdr = p.multimedija.od_vcdr if eye == "OD" else p.multimedija.os_vcdr
                    hcdr = p.multimedija.od_hcdr if eye == "OD" else p.multimedija.os_hcdr
                    acdr = p.multimedija.od_acdr if eye == "OD" else p.multimedija.os_acdr
                    rim_area = p.multimedija.od_rim_area_pixels if eye == "OD" else p.multimedija.os_rim_area_pixels

                
                json_str = p.od_vf_matrix if eye == "OD" else p.os_vf_matrix
                if json_str:
                    vf_niz = json.loads(json_str)
                    validne_tacke = [float(x) for x in vf_niz if x != -1]
                    vf_mean = np.mean(validne_tacke) if validne_tacke else 0.0
                else:
                    vf_mean = 0.0

                
                iop_corrected = float(correct_IOP(sirovi_iop or 0.0, cct_pacijenta or 540.0))

                
                privremene_posete.append([
                    iop_corrected,
                    float(vcdr or 0.0),
                    float(hcdr or 0.0),
                    float(acdr or 0.0),
                    float(rim_area or 0.0),
                    float(vf_mean)
                ])

            
            broj_poseta = len(privremene_posete)
            
            
            
            x_tensor = torch.tensor([privremene_posete], dtype=torch.float32).to(self.device)
            
            lengths_tensor = torch.tensor([broj_poseta], dtype=torch.int64).to(self.device)

            
            with torch.no_grad():
                
                preds = self.gru(x_tensor, lengths_tensor)
                
                
                
                prediktovani_vf_mean = preds[0][-1].item()

            return float(prediktovani_vf_mean)
            
    
        
        
    
    
        
        
    

ml_service = MLInferenceService()