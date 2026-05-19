from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(slots=True)
class TranslatorConfig:
    model: str
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.2
    timeout: float = 60.0
    max_chunk_chars: int = 8_000
    context_window_sentences: int = 1
    max_retries: int = 3
    retry_initial_delay: float = 1.0
    retry_max_delay: float = 30.0
    max_concurrent: int = 3
    token_counter: Callable[[str], int] | None = None

    def count_tokens(self, text: str) -> int:
        if self.token_counter is not None:
            return self.token_counter(text)
        if any("一" <= char <= "鿿" for char in text):
            return max(1, len(text) // 2)
        return max(1, len(text) // 4)
