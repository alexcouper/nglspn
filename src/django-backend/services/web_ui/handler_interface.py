from abc import ABC, abstractmethod


class WebUIHandlerInterface(ABC):
    @abstractmethod
    def revalidate_paths(self, paths: list[str]) -> None: ...
