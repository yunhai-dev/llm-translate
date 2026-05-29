from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import asyncio
import re

from bs4 import BeautifulSoup, NavigableString

from llm_translate.models import ChunkResult, TranslationResult


SKIPPED_TAGS = {"script", "style", "code", "pre", "svg", "noscript", "textarea"}


@dataclass(slots=True)
class HtmlTextNode:
    index: int
    node: NavigableString
    text: str


class SyncTextTranslator(Protocol):
    config: object

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


class AsyncTextTranslator(Protocol):
    config: object

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


def translate_html(
    translator: SyncTextTranslator,
    html: str,
    *,
    source_lang: str | None,
    target_lang: str,
    glossary: dict[str, str] | None = None,
) -> TranslationResult:
    if html == "":
        return TranslationResult(text="", chunks=[], source_lang=source_lang, target_lang=target_lang)

    soup = BeautifulSoup(html, "html.parser")
    nodes = extract_text_nodes(soup)
    translated_values = _translate_node_batches_sync(
        translator,
        nodes,
        source_lang=source_lang,
        target_lang=target_lang,
        glossary=glossary,
    )
    results: list[ChunkResult] = []

    for node, translated in zip(nodes, translated_values, strict=True):
        node.node.replace_with(translated)
        results.append(ChunkResult(index=node.index, source_text=node.text, translated_text=translated))

    return TranslationResult(text=str(soup), chunks=results, source_lang=source_lang, target_lang=target_lang)


async def atranslate_html(
    translator: AsyncTextTranslator,
    html: str,
    *,
    source_lang: str | None,
    target_lang: str,
    glossary: dict[str, str] | None = None,
) -> TranslationResult:
    if html == "":
        return TranslationResult(text="", chunks=[], source_lang=source_lang, target_lang=target_lang)

    soup = BeautifulSoup(html, "html.parser")
    nodes = extract_text_nodes(soup)
    translated_values = await _translate_node_batches_async(
        translator,
        nodes,
        source_lang=source_lang,
        target_lang=target_lang,
        glossary=glossary,
    )

    results: list[ChunkResult] = []
    for node, translated in zip(nodes, translated_values, strict=True):
        node.node.replace_with(translated)
        results.append(ChunkResult(index=node.index, source_text=node.text, translated_text=translated))

    return TranslationResult(text=str(soup), chunks=results, source_lang=source_lang, target_lang=target_lang)


def _translate_node_batches_sync(
    translator: SyncTextTranslator,
    nodes: list[HtmlTextNode],
    *,
    source_lang: str | None,
    target_lang: str,
    glossary: dict[str, str] | None,
) -> list[str]:
    translated_values: list[str] = []
    for batch in _build_node_batches(nodes, translator.config.max_chunk_chars):
        translated = translator._translate_text(
            _format_node_batch(batch),
            source_lang=source_lang,
            target_lang=target_lang,
            glossary=glossary,
        )
        try:
            translated_values.extend(_parse_batch_translation(translated, expected_count=len(batch)))
        except ValueError:
            if len(batch) == 1:
                raise
            for node in batch:
                translated_values.extend(
                    _parse_batch_translation(
                        translator._translate_text(
                            _format_node_batch([node]),
                            source_lang=source_lang,
                            target_lang=target_lang,
                            glossary=glossary,
                        ),
                        expected_count=1,
                    )
                )
    return translated_values


async def _translate_node_batches_async(
    translator: AsyncTextTranslator,
    nodes: list[HtmlTextNode],
    *,
    source_lang: str | None,
    target_lang: str,
    glossary: dict[str, str] | None,
) -> list[str]:
    batches = _build_node_batches(nodes, translator.config.max_chunk_chars)
    batch_results: list[list[str] | None] = [None] * len(batches)
    semaphore = asyncio.Semaphore(translator.config.max_concurrent)

    async def translate_one(index: int) -> None:
        batch = batches[index]
        async with semaphore:
            translated = await translator._atranslate_text(
                _format_node_batch(batch),
                source_lang=source_lang,
                target_lang=target_lang,
                glossary=glossary,
            )
        try:
            batch_results[index] = _parse_batch_translation(translated, expected_count=len(batch))
        except ValueError:
            if len(batch) == 1:
                raise
            values: list[str] = []
            for node in batch:
                async with semaphore:
                    translated = await translator._atranslate_text(
                        _format_node_batch([node]),
                        source_lang=source_lang,
                        target_lang=target_lang,
                        glossary=glossary,
                    )
                values.extend(_parse_batch_translation(translated, expected_count=1))
            batch_results[index] = values

    await asyncio.gather(*(translate_one(index) for index in range(len(batches))))

    translated_values: list[str] = []
    for result in batch_results:
        if result is not None:
            translated_values.extend(result)
    return translated_values


def _build_node_batches(nodes: list[HtmlTextNode], max_chunk_chars: int) -> list[list[HtmlTextNode]]:
    batches: list[list[HtmlTextNode]] = []
    current: list[HtmlTextNode] = []
    current_size = 0

    for node in nodes:
        item_size = len(node.text) + 32
        if current and current_size + item_size > max_chunk_chars:
            batches.append(current)
            current = []
            current_size = 0
        current.append(node)
        current_size += item_size

    if current:
        batches.append(current)
    return batches


def _format_node_batch(nodes: list[HtmlTextNode]) -> str:
    return "\n".join(f"<SEGMENT id=\"{index}\">{node.text}</SEGMENT>" for index, node in enumerate(nodes))


def _parse_batch_translation(translated: str, *, expected_count: int) -> list[str]:
    values_by_index: dict[int, str] = {}
    pattern = re.compile(r'<SEGMENT\s+id=["\'](\d+)["\']>(.*?)</SEGMENT>', re.DOTALL)
    for match in pattern.finditer(translated):
        values_by_index[int(match.group(1))] = match.group(2)

    if len(values_by_index) != expected_count:
        return [translated] if expected_count == 1 else _parse_line_fallback(translated, expected_count=expected_count)
    return [values_by_index[index] for index in range(expected_count)]


def _parse_line_fallback(translated: str, *, expected_count: int) -> list[str]:
    lines = [line.strip() for line in translated.splitlines() if line.strip()]
    if len(lines) != expected_count:
        raise ValueError("translated HTML segment count does not match source segment count")
    return lines
def extract_text_nodes(soup: BeautifulSoup) -> list[HtmlTextNode]:
    nodes: list[HtmlTextNode] = []
    for node in soup.find_all(string=True):
        if not isinstance(node, NavigableString):
            continue
        if not node.strip():
            continue
        if any(parent.name in SKIPPED_TAGS for parent in node.parents if parent.name):
            continue
        nodes.append(HtmlTextNode(index=len(nodes), node=node, text=str(node)))
    return nodes
