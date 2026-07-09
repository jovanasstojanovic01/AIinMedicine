import torch
import torch.nn as nn

class DiceLoss(nn.Module):
    def __init__(self, smooth=1e-6):
        super(DiceLoss, self).__init__()
        self.smooth = smooth

    def forward(self, preds, targets):
        
        preds = torch.sigmoid(preds)
        
        
        preds = preds.view(-1)
        targets = targets.view(-1)
        
        intersection = (preds * targets).sum()
        dice = (2. * intersection + self.smooth) / (preds.sum() + targets.sum() + self.smooth)
        
        return 1 - dice

class CombinedDiceBCELoss(nn.Module):
    def __init__(self, bce_weight=0.5, smooth=1e-6):
        super(CombinedDiceBCELoss, self).__init__()
        self.bce_weight = bce_weight
        self.bce = nn.BCEWithLogitsLoss()
        self.dice = DiceLoss(smooth)

    def forward(self, preds, targets):
        
        bce_loss = self.bce(preds, targets)
        dice_loss = self.dice(preds, targets)
        
        
        total_loss = (self.bce_weight * bce_loss) + ((1 - self.bce_weight) * dice_loss)
        return total_loss