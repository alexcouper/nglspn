from datetime import datetime

from django.conf import settings
from django.http import HttpRequest
from ninja import Router

from api.schemas.feed import FeedPageResponse
from services import REPO

router = Router()

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50

# How recent an article must be for its entry to lead the page. A single value
# rather than a constant threaded through the components that read it, because
# it is expected to change once there is real publishing volume to tune against.
DEFAULT_LEAD_FRESHNESS_DAYS = 7


@router.get(
    "",
    response={200: FeedPageResponse},
    tags=["Feed"],
    auth=None,
)
def list_feed(
    request: HttpRequest,
    before: datetime | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
) -> dict:
    """The Latest feed, newest first.

    `before` is an event time, not an offset: the stream is append-only, so a
    row never crosses a page boundary between requests.

    The lead is only sent on the first page — it is the top of the feed, and
    repeating it under every page of results would render it twice.
    """
    limit = max(1, min(limit, MAX_PAGE_SIZE))
    entries = REPO.feed.page(before=before, limit=limit + 1)

    has_more = len(entries) > limit
    entries = entries[:limit]

    lead = None
    if before is None:
        lead = REPO.feed.lead(freshness_days=_freshness_days())
        # The lead is rendered above the list; leaving it in both would show it
        # twice on the first screen.
        if lead is not None:
            entries = [e for e in entries if e.id != lead.id]

    return {
        "entries": entries,
        "next_cursor": entries[-1].occurred_at if (has_more and entries) else None,
        "lead": lead,
    }


def _freshness_days() -> int:
    return getattr(settings, "FEED_LEAD_FRESHNESS_DAYS", DEFAULT_LEAD_FRESHNESS_DAYS)
