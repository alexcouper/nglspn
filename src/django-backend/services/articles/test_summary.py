from __future__ import annotations

from services.articles.summary import derive_summary


class TestDeriveSummary:
    def test_returns_first_paragraph(self):
        body = "The opening line of the article.\n\nA second paragraph."

        assert derive_summary(body) == "The opening line of the article."

    def test_drops_leading_heading(self):
        body = "# My title\n\nThe actual opening line."

        assert derive_summary(body) == "The actual opening line."

    def test_drops_leading_image(self):
        body = "![a screenshot](https://cdn.example/x.png)\n\nThe opening line."

        assert derive_summary(body) == "The opening line."

    def test_unwraps_links_keeping_their_text(self):
        body = "See [the docs](https://example.com) for more."

        assert derive_summary(body) == "See the docs for more."

    def test_skips_a_body_that_opens_with_a_code_fence(self):
        body = "```python\nprint('hi')\n```\n\nWhat the snippet does."

        assert derive_summary(body) == "What the snippet does."

    def test_strips_list_markers_and_joins_the_lines(self):
        body = "- First point\n- Second point"

        assert derive_summary(body) == "First point Second point"

    def test_strips_emphasis_markers(self):
        body = "This is **important** and `literal`."

        assert derive_summary(body) == "This is important and literal."

    def test_leaves_underscores_inside_words_alone(self):
        body = "The hero_image_id field is the culprit."

        assert derive_summary(body) == "The hero_image_id field is the culprit."

    def test_truncates_on_a_word_boundary_with_an_ellipsis(self):
        body = "word " * 100

        assert derive_summary(body, limit=20) == "word word word word…"

    def test_empty_body_returns_empty_string(self):
        assert derive_summary("") == ""

    def test_body_with_only_a_heading_returns_empty_string(self):
        assert derive_summary("# Just a title\n") == ""
