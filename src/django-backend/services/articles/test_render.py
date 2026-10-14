from __future__ import annotations

from services.articles.render import (
    excerpt_markdown,
    render_markdown_for_email,
    split_blocks,
)

GALLERY = (
    ":::gallery\n"
    "![First](https://cdn.example/1.jpg)\n\n"
    "![Second](https://cdn.example/2.jpg)\n"
    ":::"
)
FENCE = "```python\nx = 1\n\ny = 2\n```"


def assert_sanitised_away(html: str, *fragments: str) -> None:
    for fragment in fragments:
        assert fragment not in html, f"{fragment!r} survived sanitising"


class TestSplitBlocks:
    def test_splits_paragraphs_on_blank_lines(self):
        assert split_blocks("One.\n\nTwo.\n\n\nThree.") == ["One.", "Two.", "Three."]

    def test_keeps_a_fence_with_blank_lines_as_one_block(self):
        assert split_blocks(f"Intro.\n\n{FENCE}\n\nOutro.") == [
            "Intro.",
            FENCE,
            "Outro.",
        ]

    def test_keeps_a_gallery_as_one_block(self):
        assert split_blocks(f"{GALLERY}\n\nAfter.") == [GALLERY, "After."]

    def test_tolerates_an_unclosed_fence(self):
        assert split_blocks("```\nstill code\n\nmore") == ["```\nstill code\n\nmore"]


class TestExcerptMarkdown:
    def test_returns_the_whole_body_when_short(self):
        body = "Short.\n\nAnd sweet."

        assert excerpt_markdown(body, full_max=100, excerpt_max=10) == (body, False)

    def test_cuts_on_a_block_boundary(self):
        body = "First paragraph here.\n\nSecond paragraph here.\n\nThird."

        excerpt, truncated = excerpt_markdown(body, full_max=10, excerpt_max=45)

        assert excerpt == "First paragraph here.\n\nSecond paragraph here."
        assert truncated

    def test_never_splits_a_fence(self):
        body = f"Intro.\n\n{FENCE}\n\nOutro."

        excerpt, _ = excerpt_markdown(body, full_max=10, excerpt_max=12)

        assert excerpt == "Intro."

    def test_keeps_at_least_one_block(self):
        body = "A very long opening paragraph. " * 10 + "\n\nNext."

        excerpt, truncated = excerpt_markdown(body, full_max=10, excerpt_max=20)

        assert excerpt.startswith("A very long opening")
        assert truncated


class TestRenderMarkdownForEmail:
    def test_renders_basic_markdown(self):
        html = render_markdown_for_email("## Heading\n\nSome *emphasis*.")

        assert "<h2>Heading</h2>" in html
        assert "<em>emphasis</em>" in html

    def test_strips_author_style_and_class(self):
        html = render_markdown_for_email(
            '<span class="fixed inset-0" style="position:fixed">x</span>'
        )

        assert_sanitised_away(html, "position:fixed", "fixed inset-0", "class=")
        assert "<span>x</span>" in html

    def test_drops_scripts_and_javascript_links(self):
        html = render_markdown_for_email(
            "<script>bad()</script>[click](javascript:alert(1))"
        )

        assert_sanitised_away(html, "<script", "javascript:")

    def test_keeps_figure_and_figcaption(self):
        html = render_markdown_for_email(
            '<figure><img src="https://cdn.example/a.jpg" width="800" height="600">'
            "<figcaption>A caption</figcaption></figure>"
        )

        assert "<figure>" in html
        assert "<figcaption" in html
        assert_sanitised_away(html, 'width="800"', 'height="600"')

    def test_images_get_the_email_sizing_style(self):
        html = render_markdown_for_email("![alt](https://cdn.example/a.jpg)")

        assert 'src="https://cdn.example/a.jpg"' in html
        assert "max-width:100%" in html

    def test_code_fence_gets_inline_styles_and_no_token_classes(self):
        html = render_markdown_for_email(FENCE)

        assert "<pre style=" in html
        assert_sanitised_away(html, "class=")

    def test_tables_get_borders(self):
        html = render_markdown_for_email("| a | b |\n|---|---|\n| 1 | 2 |")

        assert "<table style=" in html
        assert "<td style=" in html

    def test_flattens_a_gallery_to_stacked_images(self):
        html = render_markdown_for_email(f"Before.\n\n{GALLERY}\n\nAfter.")

        assert html.count("<img") == 2
        assert "https://cdn.example/1.jpg" in html
        assert "https://cdn.example/2.jpg" in html
        assert ":::" not in html

    def test_substitutes_image_urls(self):
        html = render_markdown_for_email(
            "![a](https://cdn.example/orig.jpg)",
            image_urls={"https://cdn.example/orig.jpg": "https://cdn.example/med.jpg"},
        )

        assert 'src="https://cdn.example/med.jpg"' in html
        assert "orig.jpg" not in html

    def test_leaves_unknown_image_urls_alone(self):
        html = render_markdown_for_email(
            "![a](https://cdn.example/other.jpg)",
            image_urls={"https://cdn.example/orig.jpg": "https://cdn.example/med.jpg"},
        )

        assert 'src="https://cdn.example/other.jpg"' in html
