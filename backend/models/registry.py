import logging
from backend.models.base import BaseSegmentationModel

logger = logging.getLogger(__name__)


class ModelRegistry:
    def __init__(self):
        self._models: dict[str, BaseSegmentationModel] = {}
        self._active: str | None = None

    def register(self, name: str, model: BaseSegmentationModel) -> None:
        logger.debug("Registering model: %s (%s)", name, type(model).__name__)
        self._models[name] = model

    async def load_model(self, name: str) -> None:
        logger.info("Loading model: %s", name)
        if name not in self._models:
            raise ValueError(f"Model '{name}' not registered")
        await self._models[name].load()
        self._active = name
        logger.info("Model activated: %s", name)

    async def unload_model(self, name: str) -> None:
        if name in self._models:
            logger.info("Unloading model: %s", name)
            await self._models[name].unload()
            if self._active == name:
                self._active = None
                logger.debug("No active model after unloading %s", name)

    async def unload_all(self) -> None:
        logger.info("Unloading all models")
        for name in self._models:
            await self._models[name].unload()
        self._active = None

    async def get_active(self) -> BaseSegmentationModel:
        if self._active is None:
            raise RuntimeError("No active model loaded")
        return self._models[self._active]

    def get_active_name(self) -> str | None:
        return self._active

    def list_models(self) -> list[dict]:
        return [
            {
                "name": name,
                "display_name": model.display_name,
                "description": model.__class__.__doc__ or "",
                "loaded": model.loaded,
            }
            for name, model in self._models.items()
        ]


_registry = ModelRegistry()


def get_registry() -> ModelRegistry:
    return _registry
