from __future__ import annotations

import asyncio
from types import SimpleNamespace

from bs4 import BeautifulSoup

from llm_translate import LLMTranslator
from llm_translate.splitters.html import extract_text_nodes


def translate_segment_payload(payload: str) -> str:
    return payload.replace(">", ">translated:").replace("translated:</SEGMENT>", "</SEGMENT>")


class FakeCompletions:
    def create(self, **kwargs):
        user_message = kwargs["messages"][1]["content"]
        text = user_message.rsplit("\n\n", 1)[1]
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=translate_segment_payload(text)))])


class FakeClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions())


class TrackingHtmlTranslator(LLMTranslator):
    def __init__(self) -> None:
        super().__init__(model="test-model", max_chunk_chars=80, max_concurrent=2)
        self.active = 0
        self.max_seen = 0
        self.calls = 0

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
        self.calls += 1
        self.active += 1
        self.max_seen = max(self.max_seen, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        return translate_segment_payload(text)


def test_extract_text_nodes_skips_code_and_script() -> None:
    soup = BeautifulSoup("<p>Hello</p><code>x = 1</code><script>alert('x')</script>", "html.parser")

    nodes = extract_text_nodes(soup)

    assert [node.text for node in nodes] == ["Hello"]


def test_translate_html_preserves_tags_and_skipped_content() -> None:
    translator = LLMTranslator(model="test-model", client=FakeClient())
    html = "<article><h1>Title</h1><p>Hello <strong>world</strong>.</p><pre>keep me</pre></article>"

    result = translator.translate_html(html, target_lang="zh")

    assert "<article>" in result.text
    assert "<strong>translated:world</strong>" in result.text
    assert "<pre>keep me</pre>" in result.text
    assert "translated:Title" in result.text
    assert len(result.chunks) == 4


def test_translate_document_html_uses_html_path() -> None:
    translator = LLMTranslator(model="test-model", client=FakeClient())

    result = translator.translate_document("<p>Hello</p>", target_lang="zh", format="html")

    assert result.text == "<p>translated:Hello</p>"


def test_async_html_translation_limits_concurrency_preserves_order_and_batches_nodes() -> None:
    async def run() -> tuple[str, int, int]:
        translator = TrackingHtmlTranslator()
        result = await translator.atranslate_html("<p>one</p><p>two</p><p>three</p>", target_lang="zh")
        return result.text, translator.max_seen, translator.calls

    text, max_seen, calls = asyncio.run(run())

    assert text == "<p>translated:one</p><p>translated:two</p><p>translated:three</p>"
    assert max_seen <= 2
    assert calls < 3
