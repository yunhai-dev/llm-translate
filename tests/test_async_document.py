from __future__ import annotations

import asyncio

from llm_translate import LLMTranslator


class TrackingTranslator(LLMTranslator):
    def __init__(self, *, max_concurrent: int) -> None:
        super().__init__(model="test-model", max_chunk_chars=7, max_concurrent=max_concurrent)
        self.active = 0
        self.max_seen = 0

    async def _atranslate_text(
        self,
        text: str,
        *,
        source_lang: str | None,
        target_lang: str,
        context_before: str = "",
        context_after: str = "",
        glossary: dict[str, str] | None = None,
    ) -> str:
        self.active += 1
        self.max_seen = max(self.max_seen, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        return f"[{text}]"


def test_async_document_translation_limits_chunk_concurrency() -> None:
    async def run() -> tuple[str, int]:
        translator = TrackingTranslator(max_concurrent=2)
        result = await translator.atranslate_document("One. Two. Three. Four.", target_lang="zh")
        return result.text, translator.max_seen

    text, max_seen = asyncio.run(run())

    assert text == "[One. ][Two. ][Three. ][Four.]"
    assert max_seen == 2


def test_async_document_translation_preserves_chunk_order() -> None:
    async def run() -> str:
        translator = TrackingTranslator(max_concurrent=4)
        result = await translator.atranslate_document("One. Two. Three. Four.", target_lang="zh")
        return result.text

    assert asyncio.run(run()) == "[One. ][Two. ][Three. ][Four.]"
