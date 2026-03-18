from __future__ import annotations

from abc import ABC, abstractmethod


class LeonardoHandlerInterface(ABC):
    @abstractmethod
    def generate(self, generation_request_id: str) -> None: ...
