from __future__ import annotations

from .client import LLMTranslator
from .models import ChunkResult, TextChunk, TranslationResult

__all__ = ["ChunkResult", "LLMTranslator", "TextChunk", "TranslationResult"]


def main() -> None:
    print("llm-translate")
