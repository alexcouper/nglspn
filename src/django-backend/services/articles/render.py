"""Render an article's markdown body for email.

The web renders article bodies in `ArticleRenderContent.tsx` with a remark and
rehype stack an email client cannot run: no `:::gallery` directive, no
stylesheet for the Prism token classes, and raw HTML from any `full_edit`
contributor has to be sanitised rather than trusted. This module is the one
Python home for turning a body into HTML, beside `summary.py` for the same
reason that module gives: a second implementation would drift.

Three stages. The block splitter keeps a fenced code block or a gallery as one
unit, so an excerpt never cuts one in half and a gallery can be flattened to
its images. python-markdown renders with the same extensions the broadcast
email uses (`MARKDOWN_EXTENSIONS`). nh3 then strips everything outside the
allowlist the web's `sanitize-schema.ts` permits, including every author
`style` and `class`, and sets our own inline styles, because email clients
ignore stylesheets.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import markdown
import nh3

if TYPE_CHECKING:
    from collections.abc import Mapping

# Shared with `render_broadcast_email`: the two email surfaces render markdown
# the same way, and a new extension is added here and nowhere else.
MARKDOWN_EXTENSIONS = ["extra", "smarty"]

_FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_GALLERY_OPEN_RE = re.compile(r"^:{3,}gallery\b")
_GALLERY_CLOSE_RE = re.compile(r"^:{3,}\s*$")
_IMAGE_LINE_RE = re.compile(r"^\s*!\[[^\]]*\]\([^)]*\)\s*$")
_SRC_RE = re.compile(r'(<img\b[^>]*\bsrc=")([^"]*)(")')


class _BlockCollector:
    """Line-by-line state for `split_blocks`.

    `fence` holds the opening marker while inside a code block, so the closing
    line has to start with the same run of backticks or tildes; `in_gallery`
    holds until a line of nothing but colons.
    """

    def __init__(self) -> None:
        self.blocks: list[str] = []
        self._current: list[str] = []
        self._fence: str | None = None
        self._in_gallery = False

    def feed(self, line: str) -> None:
        if self._fence is not None:
            self._current.append(line)
            if line.strip().startswith(self._fence):
                self._fence = None
        elif self._in_gallery:
            self._current.append(line)
            if _GALLERY_CLOSE_RE.match(line):
                self._in_gallery = False
        elif not line.strip():
            self.flush()
        else:
            self._open(line)

    def _open(self, line: str) -> None:
        opened = _FENCE_OPEN_RE.match(line)
        if opened:
            self.flush()
            self._fence = opened.group(1)
        elif _GALLERY_OPEN_RE.match(line):
            self.flush()
            self._in_gallery = True
        self._current.append(line)

    def flush(self) -> None:
        if any(line.strip() for line in self._current):
            self.blocks.append("\n".join(self._current).strip("\n"))
        self._current.clear()


def split_blocks(body: str) -> list[str]:
    """Split markdown into top-level blocks on blank lines.

    A fenced code block (``` or ~~~) and a `:::gallery` container each come
    back as a single block however many blank lines they contain.
    """
    collector = _BlockCollector()
    for line in body.splitlines():
        collector.feed(line)
    collector.flush()
    return collector.blocks


def is_gallery_block(block: str) -> bool:
    return bool(_GALLERY_OPEN_RE.match(block))


def flatten_gallery(block: str) -> str:
    """A gallery's images as one paragraph each, in document order.

    python-markdown knows nothing of directives and would print `:::gallery`
    as text. Stacking the images loses the carousel and nothing else.
    """
    lines = block.splitlines()[1:]
    if lines and _GALLERY_CLOSE_RE.match(lines[-1]):
        lines = lines[:-1]
    images = [line.strip() for line in lines if _IMAGE_LINE_RE.match(line)]
    return "\n\n".join(images)


def excerpt_markdown(body: str, *, full_max: int, excerpt_max: int) -> tuple[str, bool]:
    """Markdown to show for a lead article, and whether it was cut.

    The whole body when it is at most `full_max` characters. Otherwise whole
    blocks from the top until adding the next would pass `excerpt_max`, and at
    least one block so a long opening paragraph still shows.
    """
    if len(body) <= full_max:
        return body, False
    kept: list[str] = []
    used = 0
    for block in split_blocks(body):
        if kept and used + len(block) > excerpt_max:
            break
        kept.append(block)
        used += len(block)
    return "\n\n".join(kept), True


# GitHub-style defaults as `hast-util-sanitize` has them, plus the additions
# `sanitize-schema.ts` makes: `figure`, `figcaption`, `align` on `div`. No
# `style`, no `class`, no `width`/`height` on `img` — the inline styles below
# size images instead, so the editor's `<img width height>` cannot fight them.
ALLOWED_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "br", "hr",
    "a", "em", "strong", "b", "i", "del", "s", "sup", "sub", "kbd",
    "code", "pre", "blockquote",
    "ul", "ol", "li", "dl", "dt", "dd",
    "table", "thead", "tbody", "tr", "th", "td",
    "img", "figure", "figcaption", "div", "span",
}  # fmt: skip

ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title"},
    "div": {"align"},
    "th": {"align"},
    "td": {"align"},
    "ol": {"start"},
}

_MONO = "'SF Mono', Monaco, 'Courier New', monospace"
EMAIL_STYLES = {
    "img": {
        "style": (
            "display:block;max-width:100%;height:auto;margin:16px auto;"
            "border-radius:8px"
        )
    },
    "pre": {
        "style": (
            "background:#f1f5f9;border-radius:8px;padding:12px 16px;"
            f"overflow-x:auto;font-family:{_MONO};font-size:13px;line-height:1.5"
        )
    },
    "code": {"style": f"font-family:{_MONO};font-size:13px"},
    "blockquote": {
        "style": (
            "margin:16px 0;padding:4px 16px;border-left:3px solid #e2e8f0;color:#475569"
        )
    },
    "table": {
        "style": "border-collapse:collapse;width:100%;margin:16px 0;font-size:14px"
    },
    "th": {
        "style": (
            "border:1px solid #e2e8f0;padding:8px 10px;text-align:left;"
            "background:#f8fafc;vertical-align:top"
        )
    },
    "td": {"style": "border:1px solid #e2e8f0;padding:8px 10px;vertical-align:top"},
    "figcaption": {"style": "font-size:13px;color:#64748b;text-align:center"},
    "a": {"style": "color:#6366f1"},
}


def render_markdown_for_email(
    body: str, *, image_urls: Mapping[str, str] | None = None
) -> str:
    """Email-safe HTML for `body`.

    `image_urls` maps an image URL as written in the body to the one the email
    should use — the `medium` variant, so a reader is not sent a multi-megabyte
    original.
    """
    blocks = [
        flatten_gallery(block) if is_gallery_block(block) else block
        for block in split_blocks(body)
    ]
    html = markdown.markdown("\n\n".join(blocks), extensions=MARKDOWN_EXTENSIONS)
    html = nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        set_tag_attribute_values=EMAIL_STYLES,
        link_rel=None,
    )
    if image_urls:
        html = _SRC_RE.sub(
            lambda m: m.group(1) + image_urls.get(m.group(2), m.group(2)) + m.group(3),
            html,
        )
    return html
