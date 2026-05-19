from __future__ import annotations

import asyncio
from types import SimpleNamespace

from llm_translate import LLMTranslator


class FakeCompletions:
    def create(self, **kwargs):
        user_message = kwargs["messages"][1]["content"]
        if "TEXT_TO_TRANSLATE:" in user_message:
            text = user_message.split("TEXT_TO_TRANSLATE:\n", 1)[1].split("\n\nCONTEXT_AFTER:", 1)[0]
        else:
            text = user_message.rsplit("\n\n", 1)[1]
        if text.startswith("<SEGMENT"):
            content = text.replace(">", ">translated:").replace("translated:</SEGMENT>", "</SEGMENT>")
        else:
            content = f"translated:{text}"
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class FakeClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions())


class AsyncFakeCompletions:
    def __init__(self) -> None:
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        user_message = kwargs["messages"][1]["content"]
        if "TEXT_TO_TRANSLATE:" in user_message:
            text = user_message.split("TEXT_TO_TRANSLATE:\n", 1)[1].split("\n\nCONTEXT_AFTER:", 1)[0]
        else:
            text = user_message.rsplit("\n\n", 1)[1]
        await asyncio.sleep(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=f"translated:{text}"))])


class AsyncFakeClient:
    def __init__(self) -> None:
        self.completions = AsyncFakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


def test_async_batch_preserves_order() -> None:
    async def run() -> list[str]:
        client = AsyncFakeClient()
        translator = LLMTranslator(model="test-model", async_client=client, max_concurrent=2)
        results = await translator.atranslate_batch(["one", "two"], target_lang="zh")
        return [result.text for result in results]

    assert asyncio.run(run()) == ["translated:one", "translated:two"]


def test_sync_document_batch_preserves_order_and_format() -> None:
    client = FakeClient()
    translator = LLMTranslator(model="test-model", client=client)

    results = translator.translate_document_batch(["<p>one</p>", "<p>two</p>"], target_lang="zh", format="html")

    assert [result.text for result in results] == ["<p>translated:one</p>", "<p>translated:two</p>"]


def test_async_document_batch_preserves_order() -> None:
    async def run() -> list[str]:
        client = AsyncFakeClient()
        translator = LLMTranslator(model="test-model", async_client=client, max_concurrent=2)
        results = await translator.atranslate_document_batch(["one", "two"], target_lang="zh")
        return [result.text for result in results]

    assert asyncio.run(run()) == ["translated:one", "translated:two"]
