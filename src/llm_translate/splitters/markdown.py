from __future__ import annotations

import re
from dataclasses import dataclass

from llm_translate.utils import PlaceholderStore


@dataclass(slots=True)
class ProtectedMarkdown:
    text: str
    placeholders: PlaceholderStore

    def restore(self, translated_text: str) -> str:
        return self.placeholders.restore(translated_text)


FENCED_CODE_RE = re.compile(r"```[\s\S]*?```")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
URL_RE = re.compile(r'https?://[^\s)\]}>"\']+')


def protect_markdown(text: str) -> ProtectedMarkdown:
    placeholders = PlaceholderStore()

    def replace_code_block(match: re.Match[str]) -> str:
        return placeholders.add("CODE_BLOCK", match.group(0))

    def replace_inline_code(match: re.Match[str]) -> str:
        return placeholders.add("INLINE_CODE", match.group(0))

    def replace_url(match: re.Match[str]) -> str:
        return placeholders.add("URL", match.group(0))

    protected = FENCED_CODE_RE.sub(replace_code_block, text)
    protected = INLINE_CODE_RE.sub(replace_inline_code, protected)
    protected = URL_RE.sub(replace_url, protected)
    return ProtectedMarkdown(text=protected, placeholders=placeholders)
