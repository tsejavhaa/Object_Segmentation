import asyncio
import logging
import torch
import numpy as np
import cv2
from PIL import Image
from backend.models.base import BaseSegmentationModel
from backend.config import MODEL_CACHE_DIR

logger = logging.getLogger(__name__)


class SamSegmentationModel(BaseSegmentationModel):
    def __init__(self, model_name: str = "facebook/sam-vit-base"):
        self._model_name = model_name
        self._loaded = False
        self._pipe = None
        self.device = 0 if torch.cuda.is_available() else -1

    @property
    def name(self) -> str:
        return self._model_name.split("/")[-1]

    @property
    def display_name(self) -> str:
        return f"SAM ({self._model_name.split('/')[-1]})"

    @property
    def loaded(self) -> bool:
        return self._loaded

    async def load(self) -> None:
        logger.info("Loading model: %s on device=%s", self._model_name, self.device)
        from transformers import pipeline
        self._pipe = pipeline(
            "mask-generation",
            model=self._model_name,
            device=self.device,
            cache_dir=MODEL_CACHE_DIR,
        )
        self._loaded = True
        logger.info("Model loaded: %s", self._model_name)

    async def unload(self) -> None:
        logger.info("Unloading model: %s", self._model_name)
        del self._pipe
        self._pipe = None
        self._loaded = False
        if self.device >= 0:
            torch.cuda.empty_cache()
            logger.debug("CUDA cache cleared")

    async def segment(self, image: np.ndarray, **kwargs) -> list[np.ndarray]:
        logger.debug("Segmenting image shape=%s", image.shape)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self._pipe, pil_image)
        masks = [np.array(m, dtype=bool) for m in result["masks"]]
        logger.debug("Generated %d masks", len(masks))
        return masks