import pytest
from django.utils import timezone

from apps.articles.models import ArticleGlobalVisibility, ArticleState
from apps.feed.models import FeedEvent, FeedEventKind
from apps.projects.models import ProjectStatus
from services import HANDLERS, REPO
from tests.factories import (
    ArticleFactory,
    CompetitionFactory,
    ProjectFactory,
    UserFactory,
)


def approved_project(**kwargs):
    return ProjectFactory(
        status=ProjectStatus.APPROVED,
        approved_at=timezone.now(),
        **kwargs,
    )


def won_competition():
    competition = CompetitionFactory(winner=ProjectFactory())
    return FeedEvent.objects.get(
        competition=competition, kind=FeedEventKind.COMPETITION_WINNER
    )


def write_up(event=None, *, title="How Broadside won Chili", author=None):
    """Publish an article, optionally as the write-up of `event`."""
    project = approved_project()
    article = ArticleFactory(
        project=project,
        author=author or project.creator,
        state=ArticleState.DRAFT,
        title=title,
        about_feed_event=event,
    )
    return HANDLERS.articles.publish(article.id)


def write_up_awaiting_review(event=None, *, title="An unreviewed take"):
    """A write-up by an untrusted author: published, but `pending`."""
    return write_up(event, title=title, author=UserFactory(article_trust=False))


def rendered_ids() -> set:
    return {e.id for e in REPO.feed.page(limit=50)}


@pytest.mark.django_db
class TestSuperseding:
    def test_write_up_replaces_the_bare_event(self):
        winner_event = won_competition()

        article = write_up(winner_event)

        article_event = FeedEvent.objects.get(article=article)
        winner_event.refresh_from_db()
        assert winner_event.superseded_by_id == article_event.id
        assert winner_event.id not in rendered_ids()
        assert article_event.id in rendered_ids()

    def test_superseded_event_is_retained_not_deleted(self):
        winner_event = won_competition()

        write_up(winner_event)

        assert FeedEvent.objects.filter(pk=winner_event.pk).exists()

    def test_second_article_about_the_same_event_stands_alone(self):
        winner_event = won_competition()
        first = write_up(winner_event, title="How Broadside won")

        second = write_up(winner_event, title="A second take on Broadside")

        winner_event.refresh_from_db()
        first_event = FeedEvent.objects.get(article=first)
        second_event = FeedEvent.objects.get(article=second)
        assert winner_event.superseded_by_id == first_event.id
        assert second_event.superseded_by_id is None
        assert second_event.id in rendered_ids()

    def test_unlinked_article_leaves_the_duplicate_visible(self):
        winner_event = won_competition()

        article = write_up(None)

        winner_event.refresh_from_db()
        assert winner_event.superseded_by_id is None
        assert {winner_event.id, FeedEvent.objects.get(article=article).id} <= (
            rendered_ids()
        )

    def test_linking_after_publish_retires_the_bare_event(self):
        winner_event = won_competition()
        article = write_up(None)

        HANDLERS.feed.link_article_to_event(article, winner_event.id)

        winner_event.refresh_from_db()
        assert (
            winner_event.superseded_by_id == FeedEvent.objects.get(article=article).id
        )
        assert winner_event.id not in rendered_ids()

    def test_deleting_the_write_up_restores_the_bare_event(self):
        winner_event = won_competition()
        article = write_up(winner_event)

        HANDLERS.articles.delete_article(article.id)

        winner_event.refresh_from_db()
        assert winner_event.superseded_by_id is None
        assert winner_event.id in rendered_ids()


@pytest.mark.django_db
class TestSupersedingFollowsTheWriteUpsVisibility:
    """A supersession only holds while the write-up is actually being served.

    An article the feed will not render cannot stand in for the event it
    replaced: the bare event would be hidden as superseded, the article's own
    entry hidden as invisible, and the feed would show neither.
    """

    def test_a_write_up_awaiting_review_supersedes_nothing(self):
        winner_event = won_competition()

        article = write_up_awaiting_review(winner_event)

        winner_event.refresh_from_db()
        assert winner_event.superseded_by_id is None
        assert winner_event.id in rendered_ids()
        assert FeedEvent.objects.get(article=article).id not in rendered_ids()

    def test_approving_the_write_up_takes_the_bare_event_over(self):
        winner_event = won_competition()
        article = write_up_awaiting_review(winner_event)

        HANDLERS.articles.set_global_visibility(
            article.id, ArticleGlobalVisibility.APPROVED
        )

        winner_event.refresh_from_db()
        article_event = FeedEvent.objects.get(article=article)
        assert winner_event.superseded_by_id == article_event.id
        assert winner_event.id not in rendered_ids()
        assert article_event.id in rendered_ids()

    def test_demoting_the_write_up_gives_the_bare_event_back(self):
        winner_event = won_competition()
        article = write_up(winner_event)
        assert winner_event.id not in rendered_ids()

        HANDLERS.articles.set_global_visibility(
            article.id, ArticleGlobalVisibility.DEMOTED
        )

        winner_event.refresh_from_db()
        assert winner_event.superseded_by_id is None
        assert winner_event.id in rendered_ids()
