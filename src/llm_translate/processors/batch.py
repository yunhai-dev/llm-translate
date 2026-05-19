from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Protocol

from llm_translate.models import TranslationResult


class AsyncBatchTranslator(Protocol):
    config: object

    async def atranslate(
        self,
        text: str,
        *,
        source_lang: str | None = None,
        target_lang: str,
        glossary: dict[str, str] | None = None,
    ) -> TranslationResult: ...
    async def atranslate_document(
        self,
        text: str,
        *,
        source_lang: str | None = None,
        target_lang: str,
        glossary: dict[str, str] | None = None,
        markdown: bool = False,
        format: str | None = None,
    ) -> TranslationResult: ...


async def atranslate_batch(
    translator: AsyncBatchTranslator,
    texts: Sequence[str],
    *,
    source_lang: str | None,
    target_lang: str,
    glossary: dict[str, str] | None = None,
    max_concurrent: int,
) -> list[TranslationResult]:
    semaphore = asyncio.Semaphore(max_concurrent)
    results: list[TranslationResult | None] = [None] * len(texts)

    async def translate_one(index: int) -> None:
        async with semaphore:
            results[index] = await translator.atranslate(
                texts[index],
                source_lang=source_lang,
                target_lang=target_lang,
                glossary=glossary,
            )

    await asyncio.gather(*(translate_one(index) for index in range(len(texts))))
    return [result for result in results if result is not None]


async def atranslate_document_batch(
    translator: AsyncBatchTranslator,
    texts: Sequence[str],
    *,
    source_lang: str | None,
    target_lang: str,
    glossary: dict[str, str] | None = None,
    max_concurrent: int,
    markdown: bool = False,
    format: str | None = None,
) -> list[TranslationResult]:
    semaphore = asyncio.Semaphore(max_concurrent)
    results: list[TranslationResult | None] = [None] * len(texts)

    async def translate_one(index: int) -> None:
        async with semaphore:
            results[index] = await translator.atranslate_document(
                texts[index],
                source_lang=source_lang,
                target_lang=target_lang,
                glossary=glossary,
                markdown=markdown,
                format=format,
            )

    await asyncio.gather(*(translate_one(index) for index in range(len(texts))))
    return [result for result in results if result is not None]
