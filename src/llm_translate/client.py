from __future__ import annotations

from typing import Any

from .config import TranslatorConfig
from .models import ChunkResult, TranslationResult
from .processors import atranslate_batch, atranslate_document, atranslate_document_batch, translate_document
from .prompts import build_translation_messages
from .retry import retry_async, retry_sync
from .splitters import atranslate_html as run_atranslate_html
from .splitters import protect_markdown
from .splitters import translate_html as run_translate_html

DocumentFormat = str


class LLMTranslator:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str,
        temperature: float = 0.2,
        timeout: float = 60.0,
        max_chunk_chars: int = 8_000,
        max_retries: int = 3,
        max_concurrent: int = 3,
        client: Any | None = None,
        async_client: Any | None = None,
    ) -> None:
        self.config = TranslatorConfig(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            timeout=timeout,
            max_chunk_chars=max_chunk_chars,
            max_retries=max_retries,
            max_concurrent=max_concurrent,
        )
        self._client = client
        self._async_client = async_client

    def translate(
        self,
        text: str,
        *,
        source_lang: str | None = None,
        target_lang: str,
        glossary: dict[str, str] | None = None,
    ) -> TranslationResult:
        if text == "":
            return TranslationResult(text="", chunks=[], source_lang=source_lang, target_lang=target_lang)
        translated = self._translate_text(text, source_lang=source_lang, target_lang=target_lang, glossary=glossary)
        return TranslationResult(
            text=translated,
            chunks=[ChunkResult(index=0, source_text=text, translated_text=translated)],
            source_lang=source_lang,
            target_lang=target_lang,
        )

    async def atranslate(
        self,
        text: str,
        *,
        source_lang: str | None = None,
        target_lang: str,
        glossary: dict[str, str] | None = None,
    ) -> TranslationResult:
        if text == "":
            return TranslationResult(text="", chunks=[], source_lang=source_lang, target_lang=target_lang)
        translated = await self._atranslate_text(text, source_lang=source_lang, target_lang=target_lang, glossary=glossary)
        return TranslationResult(
            text=translated,
            chunks=[ChunkResult(index=0, source_text=text, translated_text=translated)],
            source_lang=source_lang,
            target_lang=target_lang,
        )

    def translate_document(
        self,
        text: str,
        *,
        source_lang: str | None = None,
        target_lang: str,
        glossary: dict[str, str] | None = None,
        markdown: bool = False,
        format: DocumentFormat | None = None,
    ) -> TranslationResult:
        document_format = self._resolve_document_format(format=format, markdown=markdown)
        if document_format == "html":
            return self.translate_html(text, source_lang=source_lang, target_lang=target_lang, glossary=glossary)
        protected = protect_markdown(text) if document_format == "markdown" else None
        result = translate_document(
            self,
            protected.text if protected else text,
            source_lang=source_lang,
            target_lang=target_lang,
            max_chunk_chars=self.config.max_chunk_chars,
            context_window_sentences=self.config.context_window_sentences,
            glossary=glossary,
        )
        if protected is None:
            return result
        restored_text = protected.restore(result.text)
        return TranslationResult(text=restored_text, chunks=result.chunks, source_lang=source_lang, target_lang=target_lang)

    async def atranslate_document(
        self,
        text: str,
        *,
        source_lang: str | None = None,
        target_lang: str,
        glossary: dict[str, str] | None = None,
        markdown: bool = False,
        format: DocumentFormat | None = None,
    ) -> TranslationResult:
        document_format = self._resolve_document_format(format=format, markdown=markdown)
        if document_format == "html":
            return await self.atranslate_html(text, source_lang=source_lang, target_lang=target_lang, glossary=glossary)
        protected = protect_markdown(text) if document_format == "markdown" else None
        result = await atranslate_document(
            self,
            protected.text if protected else text,
            source_lang=source_lang,
            target_lang=target_lang,
            max_chunk_chars=self.config.max_chunk_chars,
            context_window_sentences=self.config.context_window_sentences,
            max_concurrent=self.config.max_concurrent,
            glossary=glossary,
        )
        if protected is None:
            return result
        restored_text = protected.restore(result.text)
        return TranslationResult(text=restored_text, chunks=result.chunks, source_lang=source_lang, target_lang=target_lang)

    def translate_html(
        self,
        html: str,
        *,
        source_lang: str | None = None,
        target_lang: str,
        glossary: dict[str, str] | None = None,
    ) -> TranslationResult:
        return run_translate_html(
            self,
            html,
            source_lang=source_lang,
            target_lang=target_lang,
            glossary=glossary,
        )

    async def atranslate_html(
        self,
        html: str,
        *,
        source_lang: str | None = None,
        target_lang: str,
        glossary: dict[str, str] | None = None,
    ) -> TranslationResult:
        return await run_atranslate_html(
            self,
            html,
            source_lang=source_lang,
            target_lang=target_lang,
            glossary=glossary,
        )

    def translate_batch(
        self,
        texts: list[str],
        *,
        source_lang: str | None = None,
        target_lang: str,
        glossary: dict[str, str] | None = None,
    ) -> list[TranslationResult]:
        return [
            self.translate(text, source_lang=source_lang, target_lang=target_lang, glossary=glossary)
            for text in texts
        ]

    async def atranslate_batch(
        self,
        texts: list[str],
        *,
        source_lang: str | None = None,
        target_lang: str,
        glossary: dict[str, str] | None = None,
    ) -> list[TranslationResult]:
        return await atranslate_batch(
            self,
            texts,
            source_lang=source_lang,
            target_lang=target_lang,
            glossary=glossary,
            max_concurrent=self.config.max_concurrent,
        )

    def translate_document_batch(
        self,
        texts: list[str],
        *,
        source_lang: str | None = None,
        target_lang: str,
        glossary: dict[str, str] | None = None,
        markdown: bool = False,
        format: DocumentFormat | None = None,
    ) -> list[TranslationResult]:
        return [
            self.translate_document(
                text,
                source_lang=source_lang,
                target_lang=target_lang,
                glossary=glossary,
                markdown=markdown,
                format=format,
            )
            for text in texts
        ]

    async def atranslate_document_batch(
        self,
        texts: list[str],
        *,
        source_lang: str | None = None,
        target_lang: str,
        glossary: dict[str, str] | None = None,
        markdown: bool = False,
        format: DocumentFormat | None = None,
    ) -> list[TranslationResult]:
        return await atranslate_document_batch(
            self,
            texts,
            source_lang=source_lang,
            target_lang=target_lang,
            glossary=glossary,
            max_concurrent=self.config.max_concurrent,
            markdown=markdown,
            format=format,
        )

    def _translate_text(
        self,
        text: str,
        *,
        source_lang: str | None,
        target_lang: str,
        context_before: str = "",
        context_after: str = "",
        glossary: dict[str, str] | None = None,
    ) -> str:
        messages = build_translation_messages(
            text,
            source_lang,
            target_lang,
            context_before=context_before,
            context_after=context_after,
            glossary=glossary,
        )

        def operation() -> Any:
            client = self._get_client()
            return client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                timeout=self.config.timeout,
            )

        response = retry_sync(
            operation,
            max_retries=self.config.max_retries,
            initial_delay=self.config.retry_initial_delay,
            max_delay=self.config.retry_max_delay,
        )
        return self._extract_response_text(response)

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
        messages = build_translation_messages(
            text,
            source_lang,
            target_lang,
            context_before=context_before,
            context_after=context_after,
            glossary=glossary,
        )

        async def operation() -> Any:
            client = self._get_async_client()
            return await client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                timeout=self.config.timeout,
            )

        response = await retry_async(
            operation,
            max_retries=self.config.max_retries,
            initial_delay=self.config.retry_initial_delay,
            max_delay=self.config.retry_max_delay,
        )
        return self._extract_response_text(response)

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )
        return self._client

    def _get_async_client(self) -> Any:
        if self._async_client is None:
            from openai import AsyncOpenAI

            self._async_client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )
        return self._async_client

    @staticmethod
    def _extract_response_text(response: Any) -> str:
        return response.choices[0].message.content or ""

    @staticmethod
    def _resolve_document_format(*, format: DocumentFormat | None, markdown: bool) -> DocumentFormat:
        if format is None:
            return "markdown" if markdown else "text"
        if format not in {"text", "markdown", "html"}:
            raise ValueError("format must be one of: text, markdown, html")
        if markdown and format != "markdown":
            raise ValueError("markdown=True conflicts with format")
        return format
