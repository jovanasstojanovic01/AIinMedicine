
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import cv2

class DoubleConv(nn.Module):
    """(Convolution -> Batch Normalization -> ReLU) * 2"""
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.double_conv(x)

class DownSample(nn.Module):
    """Downscaling (MaxPool) + Double Convolution"""
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.down = nn.Sequential(
            nn.MaxPool2d(2),
            DoubleConv(in_channels, out_channels)
        )

    def forward(self, x):
        return self.down(x)

class UpSample(nn.Module):
    """Upscaling (ConvTranspose2d) + Concatenation (Skip Connection) + Double Convolution"""
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
        self.conv = DoubleConv(in_channels, out_channels)

    def forward(self, x1, x2):
        x1 = self.up(x1)
        
        
        diffY = x2.size()[2] - x1.size()[2]
        diffX = x2.size()[3] - x1.size()[3]
        x1 = F.pad(x1, [diffX // 2, diffX - diffX // 2, diffY // 2, diffY - diffY // 2])
        
        
        x = torch.cat([x2, x1], dim=1)
        return self.conv(x)

class RefugeUNet(nn.Module):
    def __init__(self, in_channels=3, out_channels=2):
        super().__init__()
        self.inc = DoubleConv(in_channels, 64)
        self.down1 = DownSample(64, 128)
        self.down2 = DownSample(128, 256)
        self.down3 = DownSample(256, 512)
        self.down4 = DownSample(512, 1024)
        
        self.up1 = UpSample(1024, 512)
        self.up2 = UpSample(512, 256)
        self.up3 = UpSample(256, 128)
        self.up4 = UpSample(128, 64)
        
        
        self.outc = nn.Conv2d(64, out_channels, kernel_size=1)

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)
        
        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x = self.up4(x, x1)
        
        logits = self.outc(x)
        return logits
    

    def extract_clinical_parameters(self,pred_disc, pred_cup):

        results = {
            "vCDR": 0.0,
            "hCDR": 0.0,
            "aCDR": 0.0,
            "rim_area_pixels": 0,
            "isnt_rule_valid": False,
            "quadrants_thickness": {"Inferior": 0, "Superior": 0, "Nasal": 0, "Temporal": 0},
            "diagnosis": "Healthy"
        }

        disc_img = (pred_disc * 255).astype(np.uint8)
        cup_img = (pred_cup * 255).astype(np.uint8)

        disc_contours, _ = cv2.findContours(disc_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cup_contours, _ = cv2.findContours(cup_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(disc_contours) == 0 or len(cup_contours) == 0:
            return results  

        c_disc = max(disc_contours, key=cv2.contourArea)
        c_cup = max(cup_contours, key=cv2.contourArea)

        _, _, w_disc, h_disc = cv2.boundingRect(c_disc)
        _, _, w_cup, h_cup = cv2.boundingRect(c_cup)

        
        vCDR = h_cup / max(1, h_disc)
        hCDR = w_cup / max(1, w_disc)

        
        area_disc = np.sum(pred_disc)
        area_cup = np.sum(pred_cup)
        
        aCDR = area_cup / max(1, area_disc)
        rim_area = max(0, area_disc - area_cup)

        
        
        M = cv2.moments(c_disc)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
        else:
            cX, cY = disc_img.shape[1] // 2, disc_img.shape[0] // 2

        
        
        
        
        def get_rim_thickness(direction_x, direction_y):
            """Pomoćna funkcija koja broji piksele prstena u određenom smeru od centra"""
            thickness = 0
            curr_x, curr_y = cX, cY
            h, w = pred_disc.shape
            
            
            while 0 <= curr_x < w and 0 <= curr_y < h:
                in_disc = pred_disc[curr_y, curr_x] > 0
                in_cup = pred_cup[curr_y, curr_x] > 0
                
                
                if in_disc and not in_cup:
                    thickness += 1
                    
                
                if not in_disc and thickness > 0:
                    break
                    
                curr_x += direction_x
                curr_y += direction_y
            return thickness

        
        thick_I = get_rim_thickness(0, 1)   
        thick_S = get_rim_thickness(0, -1)  
        thick_N = get_rim_thickness(-1, 0)  
        thick_T = get_rim_thickness(1, 0)   

        
        isnt_valid = (thick_I >= thick_S) and (thick_S >= thick_N) and (thick_N >= thick_T)

        
        
        if vCDR > 0.65 or (not isnt_valid and vCDR > 0.55):
            diagnosis = "Glaucoma Suspect / Positive"
        else:
            diagnosis = "Healthy"

        
        results["vCDR"] = round(float(vCDR), 3)
        results["hCDR"] = round(float(hCDR), 3)
        results["aCDR"] = round(float(aCDR), 3)
        results["rim_area_pixels"] = int(rim_area)
        results["isnt_rule_valid"] = bool(isnt_valid)
        results["quadrants_thickness"] = {
            "Inferior": thick_I,
            "Superior": thick_S,
            "Nasal": thick_N,
            "Temporal": thick_T
        }
        results["diagnosis"] = diagnosis

        return results