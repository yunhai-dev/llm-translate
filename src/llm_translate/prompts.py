from __future__ import annotations


def build_translation_messages(
    text: str,
    source_lang: str | None,
    target_lang: str,
    context_before: str = "",
    context_after: str = "",
    glossary: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    if not target_lang:
        raise ValueError("target_lang is required")

    source = source_lang or "the source language"
    rules = [
        "Preserve the original meaning.",
        "Keep formatting and line breaks as much as possible.",
        "Preserve placeholders like __CODE_BLOCK_0__, __INLINE_CODE_1__, and URLs exactly.",
        "When input contains <SEGMENT id=\"...\">...</SEGMENT>, preserve every SEGMENT tag exactly, translate only the inner text, and return the same number of segments in the same order.",
        "Do not add explanations.",
        "Return only the translated text.",
    ]
    if glossary:
        terms = "\n".join(f"- {term}: {translation}" for term, translation in glossary.items())
        rules.append(f"Use this glossary when applicable:\n{terms}")

    system = "You are a professional translator.\n\nRules:\n" + "\n".join(f"- {rule}" for rule in rules)

    if context_before or context_after:
        user = (
            f"Translate TEXT_TO_TRANSLATE from {source} to {target_lang}.\n"
            "Use CONTEXT_BEFORE and CONTEXT_AFTER only to understand meaning. "
            "Do not translate the context sections.\n\n"
            f"CONTEXT_BEFORE:\n{context_before}\n\n"
            f"TEXT_TO_TRANSLATE:\n{text}\n\n"
            f"CONTEXT_AFTER:\n{context_after}"
        )
    else:
        user = f"Translate this text from {source} to {target_lang}:\n\n{text}"

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
