from __future__ import annotations

import pytest

from llm_translate.splitters import TextSplitter


def test_short_text_stays_one_chunk() -> None:
    chunks = TextSplitter(max_chunk_chars=100).split("Hello world.")

    assert len(chunks) == 1
    assert chunks[0].text == "Hello world."


def test_long_text_splits_on_sentence_boundaries() -> None:
    chunks = TextSplitter(max_chunk_chars=12).split("One. Two. Three.")

    assert [chunk.text for chunk in chunks] == ["One. Two. ", "Three."]


def test_paragraph_newlines_are_preserved() -> None:
    text = "First paragraph.\n\nSecond paragraph."
    chunks = TextSplitter(max_chunk_chars=100).split(text)

    assert "".join(chunk.text for chunk in chunks) == text


def test_context_uses_neighbor_sentences() -> None:
    chunks = TextSplitter(max_chunk_chars=12).split("One. Two. Three.")

    assert chunks[0].context_after == "Three."
    assert chunks[1].context_before == "Two."


def test_hard_split_handles_text_without_boundaries() -> None:
    chunks = TextSplitter(max_chunk_chars=5).split("abcdefghijk")

    assert [chunk.text for chunk in chunks] == ["abcde", "fghij", "k"]


def test_splitter_rejects_invalid_chunk_size() -> None:
    with pytest.raises(ValueError):
        TextSplitter(max_chunk_chars=0)
