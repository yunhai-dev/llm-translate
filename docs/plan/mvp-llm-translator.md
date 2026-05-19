# Full LLM Translator System Design Document

## Background & Goals

- Build a complete Python package for LLM-based translation with OpenAI-compatible clients.
- The core value is reliable long-text and rich-text translation: split safely, translate chunks with context, and merge results without damaging document structure.
- Success criteria:
  - Short text can be translated through an OpenAI-compatible chat completions client.
  - Long plain text can be split by natural boundaries and translated chunk by chunk.
  - Markdown code blocks, inline code, and URLs can be protected from translation.
  - HTML/rich-text is translated with DOM-aware extraction and reconstruction, not regex-based tag rewriting.
  - Batch translation supports sync and async usage while preserving result order.
  - Tests validate every public path and every implementation stage.

## High-Level Design

Modules involved:

- `llm_translate.client`: public `LLMTranslator` API.
- `llm_translate.config`: translator configuration.
- `llm_translate.models`: chunk/result dataclasses.
- `llm_translate.prompts`: prompt construction.
- `llm_translate.retry`: retry wrapper for transient API errors.
- `llm_translate.splitters.text`: paragraph-first text splitting.
- `llm_translate.splitters.markdown`: Markdown protection for code, inline code, and URLs.
- `llm_translate.splitters.html`: DOM-aware HTML extraction, translation, and reconstruction.
- `llm_translate.processors.document`: document chunk translation and merge.
- `llm_translate.processors.batch`: async batch orchestration with concurrency limits.

Data flow:

1. Protect non-translatable structures when the format supports it.
2. Split content into chunks using format-aware boundaries.
3. Generate before/after context for each chunk.
4. Translate only the chunk body while passing context as guidance.
5. Restore protected placeholders.
6. Merge translated chunks in original order.

## Long-Text Splitting Strategy

Boundary priority:

1. Format structure:
   - Plain text: blank-line paragraphs.
   - Markdown: headings, paragraphs, lists, fenced code blocks.
   - HTML: DOM text nodes grouped by block-level elements.
2. Semantic structure:
   - Sentence endings: `。！？.!?`.
   - Secondary punctuation: `；;，,`.
3. Safe fallback:
   - Whitespace split.
   - Hard character split only when no better boundary exists.

HTML-specific considerations:

- Never split inside tags or attributes.
- Do not translate `script`, `style`, `code`, `pre`, `svg`, or hidden content.
- Preserve DOM structure and only replace selected text nodes.
- Treat block-level elements (`p`, `li`, `h1`-`h6`, `blockquote`, `td`, `th`, etc.) as natural units.
- Translate user-visible attributes such as `alt` and `title` only when explicitly enabled.
- Inline elements (`strong`, `em`, `a`, `span`) should remain attached to surrounding text where possible.

Full implementation now includes the splitter abstraction and DOM-aware HTML translation. HTML support must preserve document structure and skip non-visible or code-like content. Regex-based HTML parsing remains prohibited.

## Implementation Plan

### Stage 1: Core translator API

- **Files modified**: `src/llm_translate/__init__.py`, `src/llm_translate/client.py`, `src/llm_translate/config.py`, `src/llm_translate/models.py`, `src/llm_translate/prompts.py`, `src/llm_translate/retry.py`, `pyproject.toml`
- **Specific logic**:
  - Add `LLMTranslator` with OpenAI-compatible constructor arguments.
  - Add sync and async translation methods.
  - Build prompts that preserve placeholders and return only translated text.
  - Use the OpenAI SDK when available.
- **Validation**:
  - Mock client response parsing.
  - Invalid empty target language fails fast.

### Stage 2: Text splitting and document flow

- **Files modified**: `src/llm_translate/splitters/base.py`, `src/llm_translate/splitters/text.py`, `src/llm_translate/processors/document.py`, `src/llm_translate/client.py`
- **Specific logic**:
  - Split by paragraph first.
  - Split oversized paragraphs by sentence and punctuation.
  - Hard split only as fallback.
  - Add context-before/context-after without duplicating translated text.
  - Add `translate_document()` and `atranslate_document()`.
- **Validation**:
  - Short text remains one chunk.
  - Long paragraphs split deterministically.
  - Newlines are preserved in merged output.

### Stage 3: Batch and placeholder protection

- **Files modified**: `src/llm_translate/processors/batch.py`, `src/llm_translate/splitters/markdown.py`, `src/llm_translate/utils/placeholders.py`, `src/llm_translate/client.py`
- **Specific logic**:
  - Add async batch processing with semaphore-based concurrency.
  - Preserve result order.
  - Protect Markdown fenced code blocks, inline code, and URLs using placeholders.
  - Restore placeholders after translation.
- **Validation**:
  - Batch output order equals input order.
  - Code blocks and URLs survive unchanged.

### Stage 4: HTML/rich-text splitter

- **Files modified**: `src/llm_translate/splitters/html.py`, `src/llm_translate/client.py`, tests
- **Specific logic**:
  - Parse HTML with a DOM parser dependency.
  - Extract visible text nodes grouped by block-level ancestors.
  - Translate text groups and write translated text back into the DOM.
  - Keep skipped elements and attributes unchanged unless explicitly configured.
- **Validation**:
  - DOM remains valid after translation.
  - `script`, `style`, `pre`, and `code` are unchanged.
  - Block text is translated without losing inline tags.

### Stage 5: Tests and validation

- **Files modified**: `tests/*`
- **Specific logic**:
  - Add unit tests for splitting, placeholders, retry, prompt construction, and batch order.
- **Validation**:
  - Run test suite.
  - Run a small mocked translation flow.

## Testing Strategy

- Happy path tests:
  - Translate one short string.
  - Translate a long document split into multiple chunks.
  - Translate multiple inputs in batch.
- Error path tests:
  - Empty text returns empty translation without API call.
  - Empty target language raises `ValueError`.
  - Transient errors retry then succeed.
  - Retry exhaustion raises the final error.
- Regression scope:
  - Public imports from `llm_translate`.
  - Existing CLI `llm-translate` still works.

## Risks & Mitigation

- Token counting is model-dependent.
  - Mitigation: use conservative character estimation first and allow custom counters later.
- Chunk overlap can duplicate translated text.
  - Mitigation: use context fields in prompts instead of overlapping translatable text.
- HTML parsing is easy to break with regex.
  - Mitigation: defer full HTML support to DOM-based implementation only.
- Different OpenAI-compatible providers vary in response details.
  - Mitigation: keep response parsing narrow and test with mocked standard chat completions shape.

## Rollback Plan

- Each stage is isolated by module.
- If document translation causes issues, the short-text `translate()` path remains independently usable.
- If placeholder protection causes issues, it can be disabled by using the plain text splitter path.
