from __future__ import annotations

import re

from llm_translate.models import TextChunk

from .base import BaseSplitter


class TextSplitter(BaseSplitter):
    def __init__(self, *, max_chunk_chars: int = 8_000, context_window_sentences: int = 1) -> None:
        if max_chunk_chars <= 0:
            raise ValueError("max_chunk_chars must be positive")
        self.max_chunk_chars = max_chunk_chars
        self.context_window_sentences = context_window_sentences

    def split(self, text: str) -> list[TextChunk]:
        if text == "":
            return []
        blocks = self._split_blocks(text)
        chunks: list[str] = []
        current = ""

        for block in blocks:
            if len(block) > self.max_chunk_chars:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(self._split_oversized_block(block))
                continue

            candidate = current + block
            if current and len(candidate) > self.max_chunk_chars:
                chunks.append(current)
                current = block
            else:
                current = candidate

        if current:
            chunks.append(current)

        return self._with_context(chunks)

    def _split_blocks(self, text: str) -> list[str]:
        parts = re.split(r"(\n{2,})", text)
        blocks: list[str] = []
        for index in range(0, len(parts), 2):
            body = parts[index]
            separator = parts[index + 1] if index + 1 < len(parts) else ""
            if body or separator:
                blocks.append(body + separator)
        return blocks or [text]

    def _split_oversized_block(self, block: str) -> list[str]:
        pieces = self._split_by_boundaries(block)
        chunks: list[str] = []
        current = ""

        for piece in pieces:
            if len(piece) > self.max_chunk_chars:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(self._hard_split(piece))
                continue

            candidate = current + piece
            if current and len(candidate) > self.max_chunk_chars:
                chunks.append(current)
                current = piece
            else:
                current = candidate

        if current:
            chunks.append(current)
        return chunks

    def _split_by_boundaries(self, text: str) -> list[str]:
        pieces = re.findall(r"[^。！？.!?；;，,\n]+[。！？.!?；;，,\n]*\s*", text)
        return pieces or [text]

    def _hard_split(self, text: str) -> list[str]:
        return [text[index : index + self.max_chunk_chars] for index in range(0, len(text), self.max_chunk_chars)]

    def _with_context(self, chunks: list[str]) -> list[TextChunk]:
        text_chunks: list[TextChunk] = []
        for index, chunk in enumerate(chunks):
            context_before = self._tail_sentences(chunks[index - 1]) if index > 0 else ""
            context_after = self._head_sentences(chunks[index + 1]) if index + 1 < len(chunks) else ""
            text_chunks.append(
                TextChunk(
                    index=index,
                    text=chunk,
                    context_before=context_before,
                    context_after=context_after,
                )
            )
        return text_chunks

    def _tail_sentences(self, text: str) -> str:
        sentences = self._sentences(text)
        return "".join(sentences[-self.context_window_sentences :]).strip()

    def _head_sentences(self, text: str) -> str:
        sentences = self._sentences(text)
        return "".join(sentences[: self.context_window_sentences]).strip()

    def _sentences(self, text: str) -> list[str]:
        sentences = [sentence for sentence in re.findall(r"[^。！？.!?]+[。！？.!?]?", text) if sentence.strip()]
        return sentences or [text]
