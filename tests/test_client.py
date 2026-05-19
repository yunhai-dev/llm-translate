from __future__ import annotations

from types import SimpleNamespace

import pytest

from llm_translate import LLMTranslator


class FakeCompletions:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        user_message = kwargs["messages"][1]["content"]
        if "TEXT_TO_TRANSLATE:" in user_message:
            text = user_message.split("TEXT_TO_TRANSLATE:\n", 1)[1].split("\n\nCONTEXT_AFTER:", 1)[0]
        else:
            text = user_message.rsplit("\n\n", 1)[1]
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=f"translated:{text}"))])


class FakeClient:
    def __init__(self) -> None:
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


def test_translate_uses_chat_completions() -> None:
    client = FakeClient()
    translator = LLMTranslator(model="test-model", client=client)

    result = translator.translate("Hello", source_lang="en", target_lang="zh")

    assert result.text == "translated:Hello"
    assert client.completions.calls[0]["model"] == "test-model"


def test_translate_document_restores_markdown_placeholders() -> None:
    client = FakeClient()
    translator = LLMTranslator(model="test-model", client=client, max_chunk_chars=1_000)

    result = translator.translate_document("Use `pip install x`.", target_lang="zh", markdown=True)

    assert "`pip install x`" in result.text


def test_translate_empty_string_does_not_call_client() -> None:
    client = FakeClient()
    translator = LLMTranslator(model="test-model", client=client)

    result = translator.translate("", target_lang="zh")

    assert result.text == ""
    assert client.completions.calls == []


def test_translate_document_accepts_markdown_format() -> None:
    client = FakeClient()
    translator = LLMTranslator(model="test-model", client=client, max_chunk_chars=1_000)

    result = translator.translate_document("Use `pip install x`.", target_lang="zh", format="markdown")

    assert "`pip install x`" in result.text


def test_translate_document_rejects_invalid_format() -> None:
    translator = LLMTranslator(model="test-model", client=FakeClient())

    with pytest.raises(ValueError):
        translator.translate_document("Hello", target_lang="zh", format="pdf")


def test_missing_target_language_fails_fast() -> None:
    translator = LLMTranslator(model="test-model", client=FakeClient())

    with pytest.raises(ValueError):
        translator.translate("Hello", target_lang="")
