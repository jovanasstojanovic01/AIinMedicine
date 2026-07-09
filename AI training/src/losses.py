import torch
import torch.nn as nn


class GlaucomaVFLoss(nn.Module):
    """
    Maskirani MSE loss za per-visit regresiju VF_mean
    """

    def __init__(self):
        super(GlaucomaVFLoss, self).__init__()

    def forward(self, preds, targets, mask):
        """
        preds, targets, mask: [batch, max_steps]
        mask je 1.0 na validnim (ne-padding) pozicijama, 0.0 inače.
        """
        squared_error = (preds - targets) ** 2
        masked_error = squared_error * mask

        
        
        denom = mask.sum().clamp(min=1.0)
        return masked_error.sum() / denom