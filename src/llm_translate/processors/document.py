from __future__ import annotations

import asyncio
from typing import Protocol

from llm_translate.models import ChunkResult, TranslationResult
from llm_translate.splitters import TextSplitter


class SyncChunkTranslator(Protocol):
    def _translate_text(
        self,
        text: str,
        *,
        source_lang: str | None,
        target_lang: str,
        context_before: str = "",
        context_after: str = "",
        glossary: dict[str, str] | None = None,
    ) -> str: ...


class AsyncChunkTranslator(Protocol):
    async def _atranslate_text(
        self,
        text: str,
        *,
        source_lang: str | None,
        target_lang: str,
        context_before: str = "",
        context_after: str = "",
        glossary: dict[str, str] | None = None,
    ) -> str: ...


def translate_document(
    translator: SyncChunkTranslator,
    text: str,
    *,
    source_lang: str | None,
    target_lang: str,
    max_chunk_chars: int,
    context_window_sentences: int,
    glossary: dict[str, str] | None = None,
) -> TranslationResult:
    if text == "":
        return TranslationResult(text="", chunks=[], source_lang=source_lang, target_lang=target_lang)

    splitter = TextSplitter(max_chunk_chars=max_chunk_chars, context_window_sentences=context_window_sentences)
    text_chunks = splitter.split(text)
    results: list[ChunkResult] = []

    for chunk in text_chunks:
        translated = translator._translate_text(
            chunk.text,
            source_lang=source_lang,
            target_lang=target_lang,
            context_before=chunk.context_before,
            context_after=chunk.context_after,
            glossary=glossary,
        )
        results.append(ChunkResult(index=chunk.index, source_text=chunk.text, translated_text=translated))

    return TranslationResult(
        text="".join(result.translated_text for result in results),
        chunks=results,
        source_lang=source_lang,
        target_lang=target_lang,
    )


async def atranslate_document(
    translator: AsyncChunkTranslator,
    text: str,
    *,
    source_lang: str | None,
    target_lang: str,
    max_chunk_chars: int,
    context_window_sentences: int,
    max_concurrent: int,
    glossary: dict[str, str] | None = None,
) -> TranslationResult:
    if text == "":
        return TranslationResult(text="", chunks=[], source_lang=source_lang, target_lang=target_lang)

    splitter = TextSplitter(max_chunk_chars=max_chunk_chars, context_window_sentences=context_window_sentences)
    text_chunks = splitter.split(text)
    results: list[ChunkResult | None] = [None] * len(text_chunks)
    semaphore = asyncio.Semaphore(max_concurrent)

    async def translate_one(index: int) -> None:
        chunk = text_chunks[index]
        async with semaphore:
            translated = await translator._atranslate_text(
                chunk.text,
                source_lang=source_lang,
                target_lang=target_lang,
                context_before=chunk.context_before,
                context_after=chunk.context_after,
                glossary=glossary,
            )
        results[index] = ChunkResult(index=chunk.index, source_text=chunk.text, translated_text=translated)

    await asyncio.gather(*(translate_one(index) for index in range(len(text_chunks))))
    chunk_results = [result for result in results if result is not None]
    return TranslationResult(
        text="".join(result.translated_text for result in chunk_results),
        chunks=chunk_results,
        source_lang=source_lang,
        target_lang=target_lang,
    )
