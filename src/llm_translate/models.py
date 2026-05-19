from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TextChunk:
    index: int
    text: str
    context_before: str = ""
    context_after: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ChunkResult:
    index: int
    source_text: str
    translated_text: str
    error: Exception | None = None


@dataclass(slots=True)
class TranslationResult:
    text: str
    chunks: list[ChunkResult]
    source_lang: str | None
    target_lang: str

    def __str__(self) -> str:
        return self.text
