import torch
import torch.nn as nn

class DiceLoss(nn.Module):
    def __init__(self, smooth=1e-6):
        super(DiceLoss, self).__init__()
        # smooth sprečava deljenje sa nulom (ako su i predikcija i target potpuno prazni)
        self.smooth = smooth

    def forward(self, preds, targets):
        # Pretvaramo sirove logit-se u verovatnoće [0, 1] pre računanja Dice koeficijenta
        preds = torch.sigmoid(preds)
        
        # Ispravljamo tenzore u 1D niz radi lakšeg računanja preseka nad svim pikselima
        preds = preds.view(-1)
        targets = targets.view(-1)
        
        # Dice koeficijent meri preklapanje (Intersection over Union alternacija)
        intersection = (preds * targets).sum()
        dice = (2. * intersection + self.smooth) / (preds.sum() + targets.sum() + self.smooth)
        
        # Vraćamo 1 - Dice jer optimizator teži da minimizuje funkciju gubitka
        return 1 - dice

class CombinedDiceBCELoss(nn.Module):
    # Hibridni loss: BCE stabilizuje gradijente na nivou pojedinačnih piksela,
    # dok Dice loss optimizuje globalni oblik i rešava debalans klasa.
    def __init__(self, bce_weight=0.5, smooth=1e-6):
        super(CombinedDiceBCELoss, self).__init__()
        self.bce_weight = bce_weight
        # BCEWithLogitsLoss interno primenjuje Sigmoid, što je numerički stabilnije od čistog BCE
        self.bce = nn.BCEWithLogitsLoss()
        self.dice = DiceLoss(smooth)

    def forward(self, preds, targets):
        bce_loss = self.bce(preds, targets)
        dice_loss = self.dice(preds, targets)
        
        # Linearna kombinacija oba gubitka na osnovu definisane težine (weight=0.5)
        total_loss = (self.bce_weight * bce_loss) + ((1 - self.bce_weight) * dice_loss)
        return total_loss