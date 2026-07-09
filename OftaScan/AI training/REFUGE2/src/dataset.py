import os
import cv2
import numpy as np
from torch.utils.data import Dataset
import albumentations as A
from albumentations.pytorch import ToTensorV2
from .. import config

class RefugeDataset(Dataset):
    def __init__(self, root_dir, split='train', transforms=None):
        self.split_dir = os.path.join(root_dir, split)
        self.images_dir = os.path.join(self.split_dir, 'images')
        self.masks_dir = os.path.join(self.split_dir, 'mask')
        
        # Sorteranjem osiguravamo da se poklapaju redosledi slika i pripadajućih maski
        self.image_names = sorted(os.listdir(self.images_dir))
        self.transforms = transforms

    def __len__(self):
        return len(self.image_names)

    def __getitem__(self, idx):
        img_name = self.image_names[idx]
        img_path = os.path.join(self.images_dir, img_name)
        mask_path = os.path.join(self.masks_dir, img_name)
        
        # OpenCV podrazumevano učitava u BGR formatu, prebacujemo u RGB standard
        image = cv2.imread(img_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        if os.path.exists(mask_path):
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        else:
            mask = np.zeros((image.shape[0], image.shape[1]), dtype=np.uint8)
        
        # REFUGE2 specifičnost: disk i čašica su enkodirani različitim nivoima sive boje.
        # Pragovi < 200 i < 100 precizno izdvajaju granice optičkog diska i ekskavacije.
        disc_mask = (mask < 200).astype(np.float32)
        cup_mask = (mask < 100).astype(np.float32)
        
        # Spajamo ih u višekanalnu masku (kanal 0: disk, kanal 1: čašica)
        combined_mask = np.stack([disc_mask, cup_mask], axis=-1)
        
        if self.transforms:
            augmented = self.transforms(image=image, mask=combined_mask)
            image = augmented['image']
            combined_mask = augmented['mask']
            
            # Albumentations zadržava (H, W, C) format, PyTorch zahteva (C, H, W) za trening
            combined_mask = combined_mask.permute(2, 0, 1)
            
        return image, combined_mask

# Augmentacija za trening: povećava robusnost modela na kliničke varijacije (buka, osvetljenje, rotacije)
train_transforms = A.Compose([
    A.Resize(config.IMG_SIZE, config.IMG_SIZE),
    A.HorizontalFlip(p=0.5),
    A.VerticalFlip(p=0.5),
    A.RandomBrightnessContrast(p=0.2),
    A.ShiftScaleRotate(shift_limit=0.1, scale_limit=0.1, rotate_limit=15, p=0.5, border_mode=0),
    # ImageNet srednje vrednosti i devijacije za stabilizaciju transfer učenja
    A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ToTensorV2(),
])

# Validacione transformacije: isključivo determinističke operacije (bez nasumične augmentacije)
val_test_transforms = A.Compose([
    A.Resize(config.IMG_SIZE, config.IMG_SIZE),
    A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ToTensorV2(),
])