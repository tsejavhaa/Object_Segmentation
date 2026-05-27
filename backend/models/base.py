from abc import ABC, abstractmethod
import numpy as np
import cv2


class BaseSegmentationModel(ABC):
    @abstractmethod
    async def load(self) -> None:
        ...

    @abstractmethod
    async def unload(self) -> None:
        ...

    @abstractmethod
    async def segment(self, image: np.ndarray, **kwargs) -> list[np.ndarray]:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        ...

    @property
    @abstractmethod
    def loaded(self) -> bool:
        ...

    def _generate_colors(self, n: int) -> np.ndarray:
        np.random.seed(42)
        colors = np.random.randint(0, 255, size=(n, 3), dtype=np.uint8)
        if n > 0:
            colors[0] = [0, 255, 0]
        return colors

    async def segment_with_overlay(
        self, image: np.ndarray, alpha: float = 0.4
    ) -> tuple[list[np.ndarray], np.ndarray]:
        masks = await self.segment(image)
        if not masks:
            return masks, image.copy()

        overlay = image.copy()
        colors = self._generate_colors(len(masks))

        for i, mask in enumerate(masks):
            color = colors[i % len(colors)].tolist()
            colored_mask = np.zeros_like(image, dtype=np.uint8)
            colored_mask[mask] = color
            overlay = cv2.addWeighted(overlay, 1.0, colored_mask, alpha, 0)
            contours, _ = cv2.findContours(
                mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            cv2.drawContours(overlay, contours, -1, (255, 255, 255), 2)

        return masks, overlay