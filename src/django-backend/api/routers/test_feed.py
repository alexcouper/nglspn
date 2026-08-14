from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.articles.models import ArticleGlobalVisibility, ArticleState
from apps.feed.models import FeedEvent, FeedEventKind
from apps.projects.models import ProjectStatus
from services import HANDLERS
from services.feed.django_impl.query import MAX_PAGE_SIZE
from tests.factories import (
    ArticleFactory,
    CompetitionFactory,
    ProjectFactory,
    ProjectImageFactory,
    UserFactory,
)

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


def article_awaiting_review(*, title="Held back"):
    """What an untrusted author's publish produces: published, but `pending`."""
    article = ArticleFactory(
        project=approved_project(),
        author=UserFactory(article_trust=False),
        state=ArticleState.DRAFT,
        title=title,
    )
    return HANDLERS.articles.publish(article.id)


def get_feed(client, **params):
    response = client.get(FEED_URL, params)
    assert response.status_code == 200
    return response.json()


def entry_ids(payload) -> list[str]:
    return [entry["id"] for entry in payload["entries"]]


def served_ids(payload) -> list[str]:
    """Every entry the page renders — the lead is held out of `entries`."""
    lead = payload.get("lead")
    return ([lead["id"]] if lead else []) + entry_ids(payload)


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

    def test_paging_keeps_entries_that_share_an_occurred_at(self, client):
        """Competition milestones are dates, so exact ties are routine.

        A cursor of `occurred_at` alone drops every row tied with the page
        boundary — the rows do not reappear on the next page, they are gone.
        """
        at = timezone.now() - timedelta(days=1)
        for _ in range(3):
            approved_project(approved_at=at)

        seen = page_through(client, limit=2)

        assert len(seen) == len(set(seen)) == 3

    def test_a_cursor_that_did_not_come_from_the_api_is_rejected(self, client):
        response = client.get(FEED_URL, {"before": timezone.now().isoformat()})

        assert response.status_code == 422

    @pytest.mark.parametrize(
        "before",
        [
            "not-a-cursor",
            "|",
            # Shaped like a cursor and impossible. `parse_datetime` reads this
            # far enough to try building a date and then raises rather than
            # returning None, which is a 500 if nothing catches it.
            "2026-13-45T00:00:00|2026-01-01T00:00:00",
            "2026-01-01T00:00:00|2026-02-30T00:00:00",
        ],
    )
    def test_a_malformed_cursor_is_a_422_not_a_crash(self, client, before):
        response = client.get(FEED_URL, {"before": before})

        assert response.status_code == 422

    def test_paging_continues_at_the_largest_page_size(self, client):
        """The page size the API advertises has to be one you can page past.

        The look-ahead row that tells the router a next page exists is fetched
        by the same query as the page, so a cap applied to both reports the
        stream as exhausted at exactly the maximum limit.
        """
        for day in range(MAX_PAGE_SIZE + 5):
            approved_project(approved_at=timezone.now() - timedelta(days=day + 1))

        payload = get_feed(client, limit=MAX_PAGE_SIZE)

        assert len(payload["entries"]) == MAX_PAGE_SIZE
        assert payload["next_cursor"] is not None

    def test_paging_at_the_largest_page_size_serves_everything(self, client):
        total = MAX_PAGE_SIZE + 5
        for day in range(total):
            approved_project(approved_at=timezone.now() - timedelta(days=day + 1))

        seen = page_through(client, limit=MAX_PAGE_SIZE)

        assert len(seen) == len(set(seen)) == total

    def test_retired_entries_are_not_served(self, client):
        project = approved_project()
        event = FeedEvent.objects.get(project=project)

        HANDLERS.feed.retire(event.id)

        assert entry_ids(get_feed(client)) == []


@pytest.mark.django_db
class TestFeedSubjectVisibility:
    """An entry outlives nothing its subject does not.

    Approval appends the entry and nothing withdraws it when a project is later
    rejected or iced, so the feed has to check rather than trust the append.
    """

    @pytest.mark.parametrize(
        "hidden_status", [ProjectStatus.REJECTED, ProjectStatus.ICE_BOX]
    )
    def test_entry_disappears_when_its_project_stops_being_approved(
        self, client, hidden_status
    ):
        project = approved_project()
        assert entry_ids(get_feed(client)) != []

        project.status = hidden_status
        project.save(update_fields=["status"])

        assert entry_ids(get_feed(client)) == []

    def test_a_write_up_stops_carrying_a_hidden_projects_details(self, client):
        """The superseded side is served too, and it is a whole project ref.

        Hiding the project has to reach it, or the feed keeps publishing the
        title, tagline and icon of something the rest of the site 404s.
        """
        project = approved_project()
        published_article(
            about=FeedEvent.objects.get(project=project), title="How it was built"
        )
        assert get_feed(client)["lead"]["supersedes"] is not None

        project.status = ProjectStatus.ICE_BOX
        project.save(update_fields=["status"])

        assert get_feed(client)["lead"]["supersedes"] is None

    def test_article_entry_disappears_with_its_project(self, client):
        article = published_article()

        project = article.project
        project.status = ProjectStatus.ICE_BOX
        project.save(update_fields=["status"])

        payload = get_feed(client)
        assert payload["lead"] is None
        assert entry_ids(payload) == []

    def test_an_article_awaiting_review_is_not_served(self, client):
        article = article_awaiting_review()
        event = FeedEvent.objects.get(article=article)

        assert str(event.id) not in served_ids(get_feed(client))

    def test_approving_serves_the_entry_appended_at_publish_time(self, client):
        """Approval writes nothing to the feed.

        The entry was appended when the article published; only the read filter
        was holding it back, so flipping visibility is the whole transition.
        """
        article = article_awaiting_review()
        event = FeedEvent.objects.get(article=article)
        assert str(event.id) not in served_ids(get_feed(client))

        HANDLERS.articles.set_global_visibility(
            article.id, ArticleGlobalVisibility.APPROVED
        )

        assert str(event.id) in served_ids(get_feed(client))

    def test_demoting_an_article_withdraws_its_entry(self, client):
        article = published_article()
        event = FeedEvent.objects.get(article=article)
        assert str(event.id) in served_ids(get_feed(client))

        HANDLERS.articles.set_global_visibility(
            article.id, ArticleGlobalVisibility.DEMOTED
        )

        assert str(event.id) not in served_ids(get_feed(client))

    def test_demoting_leaves_the_admin_retirement_flag_alone(self, client):
        """`retired_at` means an admin withdrew an entry, which is not what
        demoting an article says. Overloading it would let a re-approval
        silently undo a deliberate retirement.
        """
        article = published_article()

        HANDLERS.articles.set_global_visibility(
            article.id, ArticleGlobalVisibility.DEMOTED
        )

        assert FeedEvent.objects.get(article=article).retired_at is None


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
        approved_project(approved_at=timezone.now() - timedelta(days=4))

        first = get_feed(client, limit=1)
        second = get_feed(client, before=first["next_cursor"])

        assert first["lead"] is not None
        assert second["lead"] is None

    def test_pinned_lead_is_not_repeated_on_a_later_page(self, client):
        """A pin is the one thing that puts an old entry in the lead slot.

        The first page drops the lead from its own list, so only a pinned entry
        deep in the stream can come back around as a row.
        """
        for day in range(5):
            approved_project(approved_at=timezone.now() - timedelta(days=day + 1))
        oldest = FeedEvent.objects.order_by("occurred_at").first()

        HANDLERS.feed.set_pinned(oldest.id, pinned=True)

        seen = page_through(client, limit=2)
        assert seen.count(str(oldest.id)) == 1


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

    def test_project_entry_carries_the_project_icon(self, client):
        project = approved_project()
        ProjectImageFactory(project=project, is_icon=True)

        entry = get_feed(client)["entries"][0]

        assert entry["project"]["icon_url"] is not None

    def test_tipoff_entry_carries_the_icon_too(self, client):
        project = approved_project(is_community_tipoff=True)
        ProjectImageFactory(project=project, is_icon=True)

        entry = get_feed(client)["entries"][0]

        assert entry["kind"] == FeedEventKind.PROJECT_TIPOFF
        assert entry["project"]["icon_url"] is not None

    def test_project_without_images_serves_a_null_icon(self, client):
        approved_project()

        assert get_feed(client)["entries"][0]["project"]["icon_url"] is None

    def test_article_without_an_image_serves_a_null_image_url(self, client):
        published_article()

        assert get_feed(client)["lead"]["article"]["listing_image_url"] is None


def write_up_of_a_project() -> None:
    """A write-up whose superseded event carries a project, icon and all.

    The superseded side is serialised by the same code as a top-level entry, so
    it needs the same prefetching. Kept in this fixture because a mix without it
    cannot tell whether `supersedes` costs a query per row.
    """
    project = approved_project()
    ProjectImageFactory(project=project, is_icon=True)
    published_article(
        about=FeedEvent.objects.get(project=project),
        title=f"How {project.title} was built",
    )


def seed_one_of_each() -> None:
    published_article()
    ProjectImageFactory(project=approved_project(), is_icon=True)
    approved_project(is_community_tipoff=True)
    CompetitionFactory(winner=ProjectFactory())
    write_up_of_a_project()


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

    def test_more_of_every_kind_does_not_cost_more_queries(self, client):
        """Holds the mix constant and grows it.

        Comparing across different mixes would be the wrong test: Django skips a
        nested prefetch when its parent relation is empty, so the count varies
        with which relations have rows. Only growth at a fixed shape is an N+1.
        """
        seed_one_of_each()
        baseline = count_feed_queries(client)

        for _ in range(4):
            seed_one_of_each()

        assert count_feed_queries(client) == baseline

    def test_project_icons_do_not_cost_a_query_each(self, client):
        """The icons are prefetched — adding more must not add round trips."""
        ProjectImageFactory(project=approved_project(), is_icon=True)
        baseline = count_feed_queries(client)

        for _ in range(8):
            ProjectImageFactory(project=approved_project(), is_icon=True)

        assert count_feed_queries(client) == baseline
