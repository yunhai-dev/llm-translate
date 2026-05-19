from __future__ import annotations

from llm_translate.splitters import protect_markdown


def test_protect_markdown_restores_code_and_url() -> None:
    text = "Install with `pip install x`. See https://example.com.\n\n```python\nprint('x')\n```"
    protected = protect_markdown(text)

    assert "`pip install x`" not in protected.text
    assert "https://example.com" not in protected.text
    assert "```python" not in protected.text
    assert protected.restore(protected.text) == text


def test_protect_markdown_restores_multiple_placeholders_in_order() -> None:
    text = "Use `a`, then `b`, then https://example.com/path."
    protected = protect_markdown(text)

    assert protected.text.count("__INLINE_CODE_") == 2
    assert protected.text.count("__URL_") == 1
    assert protected.restore(protected.text) == text
