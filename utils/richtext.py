"""
Utilities for working with rich-text content in Research Logger.
"""
from __future__ import annotations

import html as html_lib
import re


def looks_like_html(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r"<\s*/?\s*[a-zA-Z][^>]*>", text))


def html_to_plain_text(source: str) -> str:
    """Convert HTML-ish content into readable plain text."""
    if not source:
        return ""

    text = source

    # Preserve common block structure before stripping tags.
    text = re.sub(r"(?is)<\s*br\s*/?>", "\n", text)
    text = re.sub(r"(?is)<\s*/\s*(p|div|section|article|header|footer|h[1-6]|tr|li)\s*>", "\n", text)
    text = re.sub(r"(?is)<\s*(li|p|div|section|article|header|footer|h[1-6]|tr)\b[^>]*>", "\n", text)
    text = re.sub(r"(?is)<\s*td\b[^>]*>", "\t", text)
    text = re.sub(r"(?is)</\s*td\s*>", "\t", text)
    text = re.sub(r"(?is)<\s*th\b[^>]*>", "\t", text)
    text = re.sub(r"(?is)</\s*th\s*>", "\t", text)
    text = re.sub(r"(?is)<\s*img\b[^>]*alt=[\"']([^\"']+)[\"'][^>]*>", r"[\1]", text)
    text = re.sub(r"(?is)<\s*img\b[^>]*>", "[image]", text)

    # Strip the remaining tags and entities.
    text = re.sub(r"(?is)<[^>]+>", "", text)
    text = html_lib.unescape(text)

    # Lightweight markdown cleanup for older entries.
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*+]\s+", "- ", text, flags=re.MULTILINE)

    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def content_to_plain_text(content: str) -> str:
    if not content:
        return ""
    if looks_like_html(content):
        return html_to_plain_text(content)
    return html_lib.unescape(content).strip()
