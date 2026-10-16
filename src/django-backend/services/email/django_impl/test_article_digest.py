from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.projects.models import ImageVariant
from services.email.django_impl import render_email
from services.email.django_impl.article_digest import (
    ARTICLE_DIGEST_EXCERPT_MAX,
    LAYOUT_LEAD,
    LAYOUT_LIST,
    LAYOUT_SINGLE,
    LEAD_FULL_BODY_MAX_CHARS,
    LIST_LAYOUT_MIN_ARTICLES,
    build_article_digest,
    build_article_digest_entries,
)
from tests.factories import (
    ArticleFactory,
    NotificationFactory,
    ProjectFactory,
    PublishedAuthorArticleFactory,
    UserFactory,
    article_image,
)


def _notification(recipient=None, **article_kwargs):
    return NotificationFactory(
        recipient=recipient or UserFactory(),
        discussion=None,
        article=ArticleFactory(**article_kwargs),
    )


def _batch(count, **article_kwargs):
    """`count` notifications for one recipient, oldest article first."""
    recipient = UserFactory()
    base = timezone.now() - timedelta(days=count)
    return [
        _notification(
            recipient=recipient,
            title=f"Article {i}",
            published_at=base + timedelta(days=i),
            **article_kwargs,
        )
        for i in range(count)
    ]


def _excerpt_of(notification):
    return build_article_digest_entries([notification])[0]["body_excerpt"]


def assert_rendered_in_order(html: str, *titles: str) -> None:
    positions = [html.index(title) for title in titles]
    assert positions == sorted(positions), f"expected order {titles}"


def assert_no_greeting(rendered: str) -> None:
    assert "Hi " not in rendered
    assert "latest articles from the projects you follow" not in rendered


@pytest.mark.django_db
class TestLayoutSelection:
    def test_one_article_is_the_single_layout(self):
        digest = build_article_digest([_notification()])

        assert digest.layout == LAYOUT_SINGLE
        assert digest.template_name == "article_digest_single"

    def test_two_articles_lead_with_the_newest(self):
        digest = build_article_digest(_batch(2))

        assert digest.layout == LAYOUT_LEAD
        assert digest.context["lead"]["article_title"] == "Article 1"
        assert [e["article_title"] for e in digest.context["entries"]] == ["Article 0"]

    def test_just_under_the_cutoff_is_still_the_lead_layout(self):
        digest = build_article_digest(_batch(LIST_LAYOUT_MIN_ARTICLES - 1))

        assert digest.layout == LAYOUT_LEAD

    def test_the_cutoff_falls_back_to_the_list(self):
        digest = build_article_digest(_batch(LIST_LAYOUT_MIN_ARTICLES))

        assert digest.layout == LAYOUT_LIST
        assert digest.template_name == "article_digest"
        assert len(digest.context["entries"]) == LIST_LAYOUT_MIN_ARTICLES

    def test_list_entries_are_newest_first(self):
        digest = build_article_digest(_batch(LIST_LAYOUT_MIN_ARTICLES))

        titles = [e["article_title"] for e in digest.context["entries"]]
        assert titles == [f"Article {i}" for i in reversed(range(5))]

    def test_forced_layout_wins_over_batch_size(self):
        digest = build_article_digest([_notification()], layout=LAYOUT_LIST)

        assert digest.layout == LAYOUT_LIST

    def test_unpublished_articles_order_by_notification_time(self):
        recipient = UserFactory()
        older = _notification(recipient=recipient, title="Older", published_at=None)
        newer = _notification(recipient=recipient, title="Newer", published_at=None)

        digest = build_article_digest([older, newer])

        assert digest.context["lead"]["article_title"] == "Newer"


@pytest.mark.django_db
class TestSubject:
    def test_single_prefixes_the_project(self):
        notification = _notification(
            title="Næsta stig", project=ProjectFactory(title="Broadside")
        )

        assert build_article_digest([notification]).subject == "Broadside: Næsta stig"

    def test_single_from_the_house_project_is_the_title_alone(self):
        notification = _notification(
            title="Project Review", project=ProjectFactory(is_house_project=True)
        )

        assert build_article_digest([notification]).subject == "Project Review"

    def test_lead_names_the_newest_and_counts_the_rest(self):
        batch = _batch(3, project=ProjectFactory(title="P"))

        assert build_article_digest(batch).subject == "P: Article 2, and 2 more"

    def test_lead_applies_the_house_rule(self):
        batch = _batch(2, project=ProjectFactory(is_house_project=True))

        assert build_article_digest(batch).subject == "Article 1, and 1 more"

    def test_list_states_the_count(self):
        batch = _batch(LIST_LAYOUT_MIN_ARTICLES)

        expected = f"{LIST_LAYOUT_MIN_ARTICLES} new articles - Naglasúpan"
        assert build_article_digest(batch).subject == expected


@pytest.mark.django_db
class TestSingleArticleContext:
    def test_byline_names_project_channel_date_and_author(self):
        author = UserFactory(first_name="Anna", last_name="Jóns")
        project = ProjectFactory(title="Broadside", slug="broadside")
        notification = _notification(
            project=project,
            author=author,
            slug="results",
            published_at=timezone.now(),
        )

        article = build_article_digest([notification]).context["article"]

        assert article["project_title"] == "Broadside"
        assert article["project_url"].endswith("/projects/broadside")
        assert article["article_url"].endswith("/projects/broadside/articles/results")
        assert article["channel_name"] == "Updates"
        assert article["author_name"] == "Anna Jóns"
        assert article["published_at"] is not None

    def test_system_user_author_is_left_out_of_the_byline(self):
        notification = _notification(author=UserFactory(is_system_user=True))

        article = build_article_digest([notification]).context["article"]

        assert article["author_name"] == ""

    def test_body_images_use_the_medium_variant(self):
        notification = _notification(body="")
        image = article_image(notification.article, storage_key="articles/orig.jpg")
        ImageVariant.objects.create(
            image=image,
            size="medium",
            storage_key="articles/orig-medium.jpg",
            width=768,
            height=512,
            file_size=100,
        )
        notification.article.body = f"![pic]({image.url})"
        notification.article.save()

        article = build_article_digest([notification]).context["article"]

        assert "articles/orig-medium.jpg" in article["body_html"]
        assert 'articles/orig.jpg"' not in article["body_html"]

    def test_body_image_without_a_variant_keeps_the_original(self):
        notification = _notification(body="")
        image = article_image(notification.article, storage_key="articles/only.jpg")
        notification.article.body = f"![pic]({image.url})"
        notification.article.save()

        article = build_article_digest([notification]).context["article"]

        assert "articles/only.jpg" in article["body_html"]


@pytest.mark.django_db
class TestLeadArticleContext:
    def test_short_body_is_shown_whole(self):
        batch = _batch(2, body="Short and complete.")

        lead = build_article_digest(batch).context["lead"]

        assert lead["truncated"] is False
        assert "Short and complete." in lead["body_html"]

    def test_long_body_is_cut_on_a_block_boundary(self):
        paragraphs = [f"Paragraph {i}. " * 20 for i in range(6)]
        body = "\n\n".join(paragraphs)
        assert len(body) > LEAD_FULL_BODY_MAX_CHARS
        batch = _batch(2, body=body)

        lead = build_article_digest(batch).context["lead"]

        assert lead["truncated"] is True
        assert "Paragraph 0." in lead["body_html"]
        assert "Paragraph 5." not in lead["body_html"]


@pytest.mark.django_db
class TestRenderedTemplates:
    def test_single_html_has_body_byline_and_link(self):
        notification = _notification(
            title="The Title", body="## Heading\n\nBody text here."
        )

        digest = build_article_digest([notification])
        html, text = render_email(digest.template_name, digest.context)

        assert "The Title" in html
        assert "<h2>Heading</h2>" in html
        assert f"/articles/{notification.article.id}" in html
        assert "change your article email frequency" in html
        assert "Body text here." in text

    def test_single_text_carries_the_markdown_verbatim(self):
        body = "> Quoted & cited\n\nIf a < b, it's fine."
        notification = _notification(title="Don't escape me", body=body)

        digest = build_article_digest([notification])
        _, text = render_email(digest.template_name, digest.context)

        assert "Don't escape me" in text
        assert body in text

    def test_lead_html_shows_lead_then_the_rest(self):
        batch = _batch(3)

        digest = build_article_digest(batch)
        html, text = render_email(digest.template_name, digest.context)

        assert_rendered_in_order(html, "Article 2", "Article 1", "Article 0")
        assert "Article 0" in text

    def test_truncated_lead_offers_to_continue_reading(self):
        body = "\n\n".join(f"Paragraph {i}. " * 20 for i in range(6))
        batch = _batch(2, body=body)

        digest = build_article_digest(batch)
        html, _ = render_email(digest.template_name, digest.context)

        assert "Continue reading" in html

    def test_list_html_renders_every_entry(self):
        batch = _batch(LIST_LAYOUT_MIN_ARTICLES)

        digest = build_article_digest(batch)
        html, _ = render_email(digest.template_name, digest.context)

        for i in range(LIST_LAYOUT_MIN_ARTICLES):
            assert f"Article {i}" in html


@pytest.mark.django_db
class TestArticleDigestExcerpt:
    def test_strips_markdown_syntax_from_the_body(self):
        notification = _notification(
            body="Read the [full write-up](https://example.com/post) today."
        )

        assert _excerpt_of(notification) == "Read the full write-up today."

    def test_skips_leading_heading_and_image_blocks(self):
        notification = _notification(
            body="# The Results\n\n![](https://cdn.example.com/hero.jpg)\n\n"
            "Eight entries."
        )

        assert _excerpt_of(notification) == "Eight entries."

    def test_prefers_the_authored_summary(self):
        notification = _notification(
            body="## Ignored\n\nDerived from the body.",
            summary="The authored summary.",
        )

        assert _excerpt_of(notification) == "The authored summary."

    def test_truncates_a_long_body_on_a_word_boundary(self):
        notification = _notification(body="chili " * 200)

        excerpt = _excerpt_of(notification)
        assert len(excerpt) <= ARTICLE_DIGEST_EXCERPT_MAX + 1
        assert excerpt.endswith("chili…")

    def test_list_opens_with_the_entries_not_a_greeting(self):
        batch = _batch(LIST_LAYOUT_MIN_ARTICLES)

        digest = build_article_digest(batch)
        html, text = render_email(digest.template_name, digest.context)

        assert_no_greeting(html)
        assert_no_greeting(text)
        assert text.startswith(f"Article {LIST_LAYOUT_MIN_ARTICLES - 1}")


def _author_owned_notification(recipient=None, **article_kwargs):
    return NotificationFactory(
        recipient=recipient or UserFactory(),
        discussion=None,
        article=PublishedAuthorArticleFactory(**article_kwargs),
    )


@pytest.mark.django_db
class TestAuthorOwnedArticleInTheDigest:
    def test_byline_is_the_author_and_the_url_is_under_the_profile(self):
        author = UserFactory(first_name="Anna", last_name="Jóns")
        notification = _author_owned_notification(author=author, slug="results")

        article = build_article_digest([notification]).context["article"]

        assert article["project_title"] is None
        assert article["author_name"] == "Anna Jóns"
        assert article["author_url"].endswith(f"/users/{author.id}")
        assert article["article_url"].endswith(f"/users/{author.id}/articles/results")
        assert article["channel_name"] == ""

    def test_subject_names_the_author_where_a_project_would_be(self):
        author = UserFactory(first_name="Anna", last_name="Jóns")
        notification = _author_owned_notification(author=author, title="Results")

        assert build_article_digest([notification]).subject == "Anna Jóns: Results"

    def test_entry_has_no_icon_without_a_listing_image(self):
        notification = _author_owned_notification()

        [entry] = build_article_digest_entries([notification])

        assert entry["article_image_url"] is None
        assert entry["project_title"] is None

    def test_single_html_links_the_author_and_says_by_once(self):
        author = UserFactory(first_name="Anna", last_name="Jóns")
        notification = _author_owned_notification(author=author, title="The Title")

        digest = build_article_digest([notification])
        html, text = render_email(digest.template_name, digest.context)

        assert f"/users/{author.id}" in html
        assert html.count("Anna Jóns") == 1
        assert "by Anna Jóns" in text
        assert "Articles" not in text

    def test_lead_and_list_html_render_the_author_entry(self):
        recipient = UserFactory()
        author = UserFactory(first_name="Anna", last_name="Jóns")
        batch = [
            _author_owned_notification(
                recipient=recipient, author=author, title="Mine"
            ),
            *_batch_for(recipient, 2),
        ]

        for layout in (LAYOUT_LEAD, LAYOUT_LIST):
            digest = build_article_digest(batch, layout=layout)
            html, text = render_email(digest.template_name, digest.context)
            assert "Mine" in html
            assert f"/users/{author.id}" in html
            assert "by Anna Jóns" in text


def _batch_for(recipient, count):
    base = timezone.now() - timedelta(days=count + 1)
    return [
        _notification(
            recipient=recipient,
            title=f"Article {i}",
            published_at=base + timedelta(days=i),
        )
        for i in range(count)
    ]
