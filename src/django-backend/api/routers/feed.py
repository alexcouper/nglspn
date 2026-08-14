from django.conf import settings
from django.http import HttpRequest
from ninja import Router

from api.schemas.errors import Error
from api.schemas.feed import FeedPageResponse
from services import REPO
from services.feed.cursor import FeedCursor

router = Router()

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50

# How recent an article must be for its entry to lead the page. A single value
# rather than a constant threaded through the components that read it, because
# it is expected to change once there is real publishing volume to tune against.
DEFAULT_LEAD_FRESHNESS_DAYS = 7


@router.get(
    "",
    response={200: FeedPageResponse, 422: Error},
    tags=["Feed"],
    auth=None,
)
def list_feed(
    request: HttpRequest,
    before: str | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
) -> tuple[int, dict] | dict:
    """The Latest feed, newest first.

    `before` is an opaque cursor from a previous response's `next_cursor`, not
    an offset: the stream is append-only, so a row never crosses a page boundary
    between requests.

    The lead is only sent on the first page — it is the top of the feed, and
    repeating it under every page of results would render it twice.
    """
    cursor = None
    if before is not None:
        cursor = FeedCursor.decode(before)
        if cursor is None:
            return 422, {"detail": "Invalid cursor"}

    limit = max(1, min(limit, MAX_PAGE_SIZE))
    entries = REPO.feed.page(before=cursor, limit=limit + 1)

    has_more = len(entries) > limit
    entries = entries[:limit]
    # Taken before the lead is pulled out: the cursor marks how far the *query*
    # got, which is not affected by what the page chooses to render.
    next_cursor = (
        FeedCursor.after(entries[-1]).encode() if has_more and entries else None
    )

    lead = None
    if cursor is None:
        lead = REPO.feed.lead(freshness_days=_freshness_days())
        # A pinned lead is already held out of every page by REPO.feed.page.
        # The freshness lead is not: it is the newest entry, so it is always on
        # this first page, and leaving it in would render it twice.
        if lead is not None:
            entries = [e for e in entries if e.id != lead.id]

    return {"entries": entries, "next_cursor": next_cursor, "lead": lead}


def _freshness_days() -> int:
    return getattr(settings, "FEED_LEAD_FRESHNESS_DAYS", DEFAULT_LEAD_FRESHNESS_DAYS)
