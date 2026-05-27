import os
import logging
import logging.handlers
import queue
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from backend.routers.api import router as api_router
from backend.models.registry import get_registry
from backend.models.sam_model import SamSegmentationModel
from backend.models.segformer_model import SegFormerSegmentationModel
from backend.models.mask2former_model import Mask2FormerSegmentationModel
from backend.models.oneformer_model import OneFormerSegmentationModel

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "frontend")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

_LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

_log_file = os.path.join(_LOG_DIR, "backend.log")
_handler = logging.handlers.RotatingFileHandler(_log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

_log_queue = queue.Queue(-1)
_queue_handler = logging.handlers.QueueHandler(_log_queue)
_queue_listener = logging.handlers.QueueListener(_log_queue, _handler, respect_handler_level=True)
_queue_listener.start()

_logger = logging.getLogger("backend")
_logger.setLevel(logging.DEBUG)
_logger.addHandler(_queue_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry = get_registry()
    registry.register("sam3", SamSegmentationModel(model_name="facebook/sam-vit-base"))
    registry.register("sam2", SamSegmentationModel(model_name="facebook/sam-vit-huge"))
    registry.register("segformer",
        SegFormerSegmentationModel(model_name="nvidia/segformer-b0-finetuned-ade-512-512"))
    registry.register("mask2former",
        Mask2FormerSegmentationModel(model_name="facebook/mask2former-swin-small-coco-instance"))
    registry.register("oneformer",
        OneFormerSegmentationModel(model_name="shi-labs/oneformer_ade20k_swin_tiny"))
    await registry.load_model("sam3")
    yield
    await registry.unload_all()


app = FastAPI(title="Object Segmentation App", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

if os.path.exists(UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")