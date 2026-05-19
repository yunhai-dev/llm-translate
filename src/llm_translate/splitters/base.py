from __future__ import annotations

from abc import ABC, abstractmethod

from llm_translate.models import TextChunk


class BaseSplitter(ABC):
    @abstractmethod
    def split(self, text: str) -> list[TextChunk]:
        raise NotImplementedError
