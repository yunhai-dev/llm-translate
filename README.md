# openai-llm-translate

A Python translation toolkit for OpenAI-compatible LLM APIs. It supports plain text, long documents, Markdown, HTML/rich text, batch translation, retries, glossary hints, and controlled async concurrency.

## Features

- OpenAI SDK-compatible sync and async clients
- Plain text translation for short strings
- Long document splitting with context windows
- Markdown protection for code blocks, inline code, and URLs
- DOM-aware HTML translation with preserved tags and skipped code/script blocks
- Batched HTML text-node translation to reduce API calls
- Batch document translation
- Retry handling for transient API errors
- Configurable async concurrency via `max_concurrent`

## Installation

This project uses `uv`:

```bash
uv sync
```

Or install the package in editable mode from this repository:

```bash
uv pip install -e .
```

## Configuration

The package works with OpenAI-compatible APIs. Keep secrets in environment variables:

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4o-mini"
```

`OPENAI_BASE_URL` is optional when using the default OpenAI endpoint.

## Quick start

```python
from llm_translate import LLMTranslator

translator = LLMTranslator(
    api_key="your-api-key",
    base_url="https://api.openai.com/v1",
    model="gpt-4o-mini",
)

result = translator.translate(
    "Large language models can translate text.",
    source_lang="en",
    target_lang="zh-CN",
)

print(result.text)
```

## Long document translation

Long documents are split into chunks, translated with neighboring context, and merged back in source order.

```python
result = translator.translate_document(
    long_text,
    source_lang="en",
    target_lang="zh-CN",
)

print(result.text)
print(len(result.chunks))
```

## Markdown translation

Markdown mode protects fenced code blocks, inline code, and URLs before translation, then restores them after translation.

```python
result = translator.translate_document(
    markdown_text,
    source_lang="en",
    target_lang="zh-CN",
    format="markdown",
)
```

The older `markdown=True` option is also supported:

```python
result = translator.translate_document(markdown_text, target_lang="zh-CN", markdown=True)
```

## HTML translation

HTML mode parses the document with BeautifulSoup, translates visible text nodes, preserves the DOM structure, and skips tags such as `script`, `style`, `code`, `pre`, `svg`, `noscript`, and `textarea`.

```python
result = translator.translate_document(
    "<article><h1>Hello</h1><p>World</p></article>",
    source_lang="en",
    target_lang="zh-CN",
    format="html",
)

print(result.text)
```

For async HTML translation, text nodes are grouped into segment batches and requests are limited by `max_concurrent`.

```python
import asyncio

async def main() -> None:
    translator = LLMTranslator(
        api_key="your-api-key",
        model="gpt-4o-mini",
        max_chunk_chars=1000,
        max_concurrent=3,
    )
    result = await translator.atranslate_document(
        html_text,
        source_lang="zh-CN",
        target_lang="en",
        format="html",
    )
    print(result.text)

asyncio.run(main())
```

## Batch translation

```python
results = translator.translate_document_batch(
    ["First document.", "Second document."],
    source_lang="en",
    target_lang="zh-CN",
)

print([result.text for result in results])
```

Async batch translation preserves input order while limiting concurrency:

```python
results = await translator.atranslate_document_batch(
    documents,
    source_lang="en",
    target_lang="zh-CN",
)
```

## Glossary hints

Pass a glossary to bias term translation:

```python
result = translator.translate_document(
    text,
    source_lang="en",
    target_lang="zh-CN",
    glossary={"watch": "手表", "battery life": "电池续航"},
)
```

## Real API example

Run the included example after setting environment variables:

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL="gpt-4o-mini"
uv run python examples/real_translation.py
```

Optional tuning:

```bash
export OPENAI_BASE_URL="https://api.openai.com/v1"
export TRANSLATE_MAX_CHUNK_CHARS="1000"
export TRANSLATE_MAX_CONCURRENT="3"
export TRANSLATE_MAX_RETRIES="2"
```

## Development

Run tests:

```bash
uv run pytest
```

Current test coverage includes text splitting, Markdown protection, client APIs, retry behavior, batch flows, async document concurrency, and HTML translation.

## Release

Publishing is handled by GitHub Actions when a version tag is pushed.

Before the first release, configure PyPI Trusted Publishing for this repository:

- PyPI project name: `openai-llm-translate`
- Repository owner: `yunhai-dev`
- Repository name: `llm-translate`
- Workflow name: `publish.yml`
- Environment name: `pypi`

Then create and push a version tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The workflow runs the test suite, builds the package with `uv build`, and publishes with `uv publish`.

## Project status

This package is under active development. The current implementation focuses on robust OpenAI-compatible translation flows for text, Markdown, and HTML documents.
