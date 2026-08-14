from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.articles.models import ArticleState
from apps.feed.models import FeedEvent, FeedEventKind
from apps.projects.models import ProjectStatus
from services import HANDLERS
from tests.factories import ArticleFactory, CompetitionFactory, ProjectFactory

FEED_URL = "/api/feed"


def approved_project(**kwargs):
    return ProjectFactory(
        status=ProjectStatus.APPROVED,
        approved_at=kwargs.pop("approved_at", timezone.now()),
        **kwargs,
    )


def published_article(*, published_at=None, about=None, title="A write-up"):
    article = ArticleFactory(
        project=approved_project(),
        state=ArticleState.DRAFT,
        title=title,
        about_feed_event=about,
    )
    return HANDLERS.articles.publish(article.id, published_at=published_at)


def get_feed(client, **params):
    response = client.get(FEED_URL, params)
    assert response.status_code == 200
    return response.json()


def entry_ids(payload) -> list[str]:
    return [entry["id"] for entry in payload["entries"]]


def page_through(client, *, limit: int) -> list[str]:
    seen: list[str] = []
    cursor = None
    while True:
        params = {"limit": limit}
        if cursor:
            params["before"] = cursor
        payload = get_feed(client, **params)
        if payload.get("lead"):
            seen.append(payload["lead"]["id"])
        seen.extend(entry_ids(payload))
        cursor = payload["next_cursor"]
        if not cursor:
            return seen


@pytest.mark.django_db
class TestFeedPaging:
    def test_empty_stream_returns_no_entries_and_no_lead(self, client):
        payload = get_feed(client)

        assert payload["entries"] == []
        assert payload["lead"] is None
        assert payload["next_cursor"] is None

    def test_entries_are_newest_first(self, client):
        old = approved_project(approved_at=timezone.now() - timedelta(days=10))
        recent = approved_project(approved_at=timezone.now() - timedelta(days=1))

        payload = get_feed(client)

        ordered = [entry["project"]["title"] for entry in payload["entries"]]
        assert ordered == [recent.title, old.title]

    def test_paging_serves_each_entry_exactly_once(self, client):
        for day in range(7):
            approved_project(approved_at=timezone.now() - timedelta(days=day + 1))

        seen = page_through(client, limit=2)

        assert len(seen) == len(set(seen)) == 7

    def test_retired_entries_are_not_served(self, client):
        project = approved_project()
        event = FeedEvent.objects.get(project=project)

        HANDLERS.feed.retire(event.id)

        assert entry_ids(get_feed(client)) == []


@pytest.mark.django_db
class TestFeedLead:
    def test_recent_article_leads(self, client):
        article = published_article()

        payload = get_feed(client)

        assert payload["lead"]["article"]["title"] == article.title

    def test_stale_article_does_not_lead(self, client):
        published_article(published_at=timezone.now() - timedelta(days=30))

        payload = get_feed(client)

        assert payload["lead"] is None

    def test_bare_event_does_not_lead(self, client):
        approved_project()

        payload = get_feed(client)

        assert payload["lead"] is None

    def test_lead_is_not_repeated_in_the_entry_list(self, client):
        published_article()

        payload = get_feed(client)

        assert payload["lead"]["id"] not in entry_ids(payload)

    def test_pin_overrides_freshness(self, client):
        stale = published_article(published_at=timezone.now() - timedelta(days=30))
        event = FeedEvent.objects.get(article=stale)

        HANDLERS.feed.set_pinned(event.id, pinned=True)

        payload = get_feed(client)
        assert payload["lead"]["id"] == str(event.id)

    def test_lead_is_only_sent_on_the_first_page(self, client):
        published_article()
        approved_project(approved_at=timezone.now() - timedelta(days=3))

        payload = get_feed(client, before=timezone.now().isoformat())

        assert payload["lead"] is None


@pytest.mark.django_db
class TestFeedEntryShape:
    def test_write_up_carries_the_flag_of_the_event_it_replaced(self, client):
        competition = CompetitionFactory(winner=ProjectFactory())
        winner_event = FeedEvent.objects.get(
            competition=competition, kind=FeedEventKind.COMPETITION_WINNER
        )

        published_article(about=winner_event, title="How it was won")

        payload = get_feed(client)
        lead = payload["lead"]
        assert lead["article"]["title"] == "How it was won"
        assert lead["supersedes"]["kind"] == FeedEventKind.COMPETITION_WINNER
        assert lead["supersedes"]["competition"]["name"] == competition.name

    def test_standalone_article_has_no_superseded_context(self, client):
        published_article()

        assert get_feed(client)["lead"]["supersedes"] is None

    def test_tipoff_entry_is_distinguishable_from_a_new_project(self, client):
        approved_project(is_community_tipoff=True)

        kinds = [entry["kind"] for entry in get_feed(client)["entries"]]
        assert kinds == [FeedEventKind.PROJECT_TIPOFF]

    def test_article_without_an_image_serves_a_null_image_url(self, client):
        published_article()

        assert get_feed(client)["lead"]["article"]["listing_image_url"] is None


def count_feed_queries(client) -> int:
    with CaptureQueriesContext(connection) as captured:
        get_feed(client)
    return len(captured)


@pytest.mark.django_db(transaction=False)
class TestFeedQueryCount:
    def test_more_entries_do_not_cost_more_queries(self, client):
        """The guard against N+1: cost must be flat in the number of rows."""
        for day in range(3):
            approved_project(approved_at=timezone.now() - timedelta(days=day + 1))
        with_three = count_feed_queries(client)

        for day in range(3, 15):
            approved_project(approved_at=timezone.now() - timedelta(days=day + 1))
        with_fifteen = count_feed_queries(client)

        assert with_fifteen == with_three

    def test_mixed_entry_kinds_do_not_cost_more_queries(self, client):
        approved_project()
        baseline = count_feed_queries(client)

        published_article()
        approved_project(is_community_tipoff=True)
        CompetitionFactory(winner=ProjectFactory())

        assert count_feed_queries(client) == baseline
