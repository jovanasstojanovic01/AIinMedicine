import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'glaucoma.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REFUGEUNET_WEIGHTS = os.getenv(
        "REFUGEUNET_WEIGHTS", os.path.join(BASE_DIR, "checkpoints", "refugeunet_best.pth")
    )
    LSTM_WEIGHTS = os.getenv(
        "LSTM_WEIGHTS", os.path.join(BASE_DIR, "checkpoints", "lstm_best_overall.pth")
    )
    XGB_MODEL = os.getenv(
        "XGB_MODEL", os.path.join(BASE_DIR, "checkpoints", "xgb_best_overall.pkl")
    )
    SCALER_PATH = os.getenv(
        "SCALER_PATH", os.path.join(BASE_DIR, "checkpoints", "scaler.pkl")
    )

    VF_POINTS = 61

    EXTRA_FEATURES = 5

    INPUT_FEATURES = VF_POINTS + EXTRA_FEATURES  

    MAX_TIMESTEPS = 10

    HIDDEN_SIZE = 64
    NUM_LAYERS = 2
    DROPOUT = 0.3

    CFP_IMAGE_SIZE = 512
    CFP_UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "cfp_images")

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 