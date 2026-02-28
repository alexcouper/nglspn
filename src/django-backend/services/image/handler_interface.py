from __future__ import annotations

from abc import ABC, abstractmethod


class ImageHandlerInterface(ABC):
    @abstractmethod
    def generate_variants(self, image_id: str) -> None: ...
