import torch

# Putanje do podataka
DATA_DIR = "./data/refuge2"
CHECKPOINT_DIR = "./checkpoints"
OUTPUT_DIR = "./outputs"

# Hiperparametri za slike
IMG_SIZE = 512  # Možeš smanjiti na 256 ako ponestane memorije na grafičkoj

# Hiperparametri za trening
BATCH_SIZE = 4  # Prilagodi svom hardveru (8 ili 16)
LEARNING_RATE = 1e-4
EPOCHS = 50

# Hardver
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Multi-task loss težine (možemo ih fino podešavati kasnije)
# Pošto imamo 3 zadatka: segmentacija, lokalizacija (fovea), klasifikacija (glaukom)
LOSS_WEIGHTS = {
    "segmentation": 1.0,
    "localization": 0.5,
    "classification": 0.5
}