import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
IMAGE_DIR = os.path.join(UPLOAD_DIR, "images")
VIDEO_DIR = os.path.join(UPLOAD_DIR, "videos")
RESULT_DIR = os.path.join(UPLOAD_DIR, "results")

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

DEFAULT_MODEL = "facebook/sam-vit-base"
SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".mp4", ".avi", ".mov", ".mkv"}

MODELS_DIR = os.path.join(BASE_DIR, "backend", "models")
MODEL_CACHE_DIR = os.path.join(MODELS_DIR, ".cache")
os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
