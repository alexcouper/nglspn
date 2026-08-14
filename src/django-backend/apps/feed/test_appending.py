from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.articles.models import ArticleState
from apps.feed.models import FeedEvent, FeedEventKind
from apps.projects.models import ProjectStatus
from services import HANDLERS
from tests.factories import (
    ArticleFactory,
    CompetitionFactory,
    DiscussionFactory,
    ProjectFactory,
)


def kinds_for(**subject) -> list[str]:
    return list(FeedEvent.objects.filter(**subject).values_list("kind", flat=True))


def approved_project(**kwargs):
    return ProjectFactory(
        status=ProjectStatus.APPROVED,
        approved_at=kwargs.pop("approved_at", timezone.now()),
        **kwargs,
    )


def published_article(project=None, *, published_at=None, **kwargs):
    article = ArticleFactory(
        project=project or approved_project(),
        state=ArticleState.DRAFT,
        **kwargs,
    )
    return HANDLERS.articles.publish(article.id, published_at=published_at)


@pytest.mark.django_db
class TestArticleAppends:
    def test_publishing_appends_one_event_at_published_at(self):
        article = published_article()

        events = FeedEvent.objects.filter(article=article)
        assert [e.kind for e in events] == [FeedEventKind.ARTICLE_PUBLISHED]
        assert events[0].occurred_at == article.published_at

    def test_backdated_publish_lands_at_the_backdated_time(self):
        backdated = timezone.now() - timedelta(days=40)

        article = published_article(published_at=backdated)

        event = FeedEvent.objects.get(article=article)
        assert event.occurred_at == backdated

    def test_editing_a_published_article_appends_nothing(self):
        article = published_article()

        HANDLERS.articles.update_article(article.id, title="Edited afterwards")

        assert FeedEvent.objects.filter(article=article).count() == 1

    def test_draft_article_has_no_event(self):
        ArticleFactory(project=approved_project(), state=ArticleState.DRAFT)

        assert (
            FeedEvent.objects.filter(kind=FeedEventKind.ARTICLE_PUBLISHED).count() == 0
        )


@pytest.mark.django_db
class TestProjectAppends:
    def test_approved_project_appends_a_new_project_event(self):
        project = approved_project()

        assert kinds_for(project=project) == [FeedEventKind.PROJECT_PUBLISHED]

    def test_approved_tipoff_appends_a_tipoff_event_instead(self):
        project = approved_project(is_community_tipoff=True)

        assert kinds_for(project=project) == [FeedEventKind.PROJECT_TIPOFF]

    def test_unapproved_project_has_no_event(self):
        project = ProjectFactory(status=ProjectStatus.PENDING)

        assert kinds_for(project=project) == []

    def test_event_time_matches_approval_not_submission(self):
        approved_at = timezone.now() - timedelta(days=5)

        project = approved_project(
            approved_at=approved_at,
            published_at=timezone.now() - timedelta(days=9),
        )

        assert FeedEvent.objects.get(project=project).occurred_at == approved_at

    def test_re_saving_an_approved_project_appends_nothing_further(self):
        project = approved_project()

        project.title = "Renamed"
        project.save()

        assert FeedEvent.objects.filter(project=project).count() == 1


@pytest.mark.django_db
class TestCompetitionAppends:
    def test_competition_gets_an_opened_event_at_its_start_date(self):
        competition = CompetitionFactory(start_date=date(2025, 3, 1))

        event = FeedEvent.objects.get(
            competition=competition, kind=FeedEventKind.COMPETITION_OPENED
        )
        assert event.occurred_at.date() == date(2025, 3, 1)

    def test_announcing_a_winner_appends_a_winner_event(self):
        competition = CompetitionFactory()

        competition.winner = ProjectFactory()
        competition.save()

        event = FeedEvent.objects.get(
            competition=competition, kind=FeedEventKind.COMPETITION_WINNER
        )
        assert event.occurred_at == competition.winner_announced_at

    def test_winner_event_is_not_duplicated_when_the_winner_changes(self):
        competition = CompetitionFactory(winner=ProjectFactory())

        competition.winner = ProjectFactory()
        competition.save()

        assert (
            FeedEvent.objects.filter(
                competition=competition, kind=FeedEventKind.COMPETITION_WINNER
            ).count()
            == 1
        )

    def test_competition_without_a_winner_has_no_winner_event(self):
        competition = CompetitionFactory()

        assert (
            FeedEvent.objects.filter(
                competition=competition, kind=FeedEventKind.COMPETITION_WINNER
            ).count()
            == 0
        )


@pytest.mark.django_db
class TestSourcesThatAppendNothing:
    def test_creating_a_discussion_appends_nothing(self):
        DiscussionFactory(project=approved_project())

        assert (
            FeedEvent.objects.filter(kind=FeedEventKind.DISCUSSION_PROMOTED).count()
            == 0
        )

    def test_replying_to_a_discussion_appends_nothing(self):
        thread = DiscussionFactory(project=approved_project())

        DiscussionFactory(project=thread.project, parent=thread)

        assert (
            FeedEvent.objects.filter(kind=FeedEventKind.DISCUSSION_PROMOTED).count()
            == 0
        )

    def test_deleting_a_published_article_removes_its_entry(self):
        article = published_article()

        HANDLERS.articles.delete_article(article.id)

        assert FeedEvent.objects.filter(article_id=article.id).count() == 0

    def test_promoting_a_discussion_is_what_appends(self):
        discussion = DiscussionFactory(project=approved_project())

        HANDLERS.feed.promote_discussion(discussion)

        assert kinds_for(discussion=discussion) == [FeedEventKind.DISCUSSION_PROMOTED]
