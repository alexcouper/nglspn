"""Derive a listing summary from an article's markdown body.

Used when an article has no authored summary. Every surface that shows an
article excerpt goes `article.summary or derive_summary(article.body)`:
`ArticleOut.summary_display`, `ArticleListItem.summary`, the digest email and
the notification bell. Lives only here — a second implementation would drift,
in Python as easily as in TypeScript, so the frontend previews a saved article
rather than deriving client-side.

Discussion bodies are NOT markdown and must not come through here; see
`services/notifications/django_impl/handler.py::_plain_text_excerpt`.
"""

from __future__ import annotations

import re

# Order matters below: fences and headings go before block splitting so a body
# that opens with either falls through to the first real paragraph, and images
# are removed before links because image syntax contains link syntax.
_FENCE_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
_HEADING_LINE_RE = re.compile(r"^ {0,3}#{1,6}\s.*$", re.MULTILINE)
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_LINE_MARKER_RE = re.compile(r"^ {0,3}(?:>\s*|[-*+]\s+|\d+[.)]\s+)")
# Underscores are left alone on purpose: stripping them mangles snake_case
# identifiers, which show up constantly in this product's articles.
_EMPHASIS_RE = re.compile(r"[*`~]")
_WHITESPACE_RE = re.compile(r"\s+")


def derive_summary(body: str, limit: int = 200) -> str:
    """Return a plain-text excerpt of ``body``, or "" if there is nothing to say."""
    text = _FENCE_RE.sub("", body)
    text = _HEADING_LINE_RE.sub("", text)
    text = _IMAGE_RE.sub("", text)
    text = _LINK_RE.sub(r"\1", text)
    text = _HTML_TAG_RE.sub("", text)

    for block in text.split("\n\n"):
        lines = [_LINE_MARKER_RE.sub("", line) for line in block.splitlines()]
        candidate = _EMPHASIS_RE.sub("", " ".join(lines))
        candidate = _WHITESPACE_RE.sub(" ", candidate).strip()
        if candidate:
            return _truncate(candidate, limit)
    return ""


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:—-")
    return f"{cut}…"
