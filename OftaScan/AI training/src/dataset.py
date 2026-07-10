import numpy as np
import torch
from torch.utils.data import Dataset


class GlaucomaTemporalDataset(Dataset):

    def __init__(self, x_path, y_path, mask_path):
        self.X = np.load(x_path)
        self.y = np.load(y_path)
        self.mask = np.load(mask_path)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        seq = torch.tensor(self.X[idx], dtype=torch.float32)
        target = torch.tensor(self.y[idx], dtype=torch.float32)
        mask = torch.tensor(self.mask[idx], dtype=torch.float32)
        return seq, target, mask