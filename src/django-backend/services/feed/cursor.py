"""The pagination cursor for the Latest feed.

`occurred_at` alone is not a cursor. Competition milestones are dates, so the
appender maps them to local midnight and two competitions that opened on the
same day land on the identical timestamp. Paging with `occurred_at < ?` then
drops every row that ties with the page boundary, silently.

The cursor therefore carries both keys the stream is ordered by —
`(occurred_at, created_at)` — and the read path compares them as a pair.
`created_at` is `auto_now_add`, so it is distinct per row and gives the
comparison a total order.

It is opaque on purpose: callers pass `next_cursor` back untouched rather than
constructing one, which keeps the encoding free to change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.utils.dateparse import parse_datetime

if TYPE_CHECKING:
    from datetime import datetime

    from apps.feed.models import FeedEvent

SEPARATOR = "|"


@dataclass(frozen=True)
class FeedCursor:
    occurred_at: datetime
    created_at: datetime

    @classmethod
    def after(cls, event: FeedEvent) -> FeedCursor:
        """The position just past `event` — the last entry of a page."""
        return cls(occurred_at=event.occurred_at, created_at=event.created_at)

    @classmethod
    def decode(cls, raw: str) -> FeedCursor | None:
        """Parse a cursor, or None if it did not come from `encode`."""
        occurred_at, separator, created_at = raw.partition(SEPARATOR)
        if not separator:
            return None
        parsed_occurred = parse_datetime(occurred_at)
        parsed_created = parse_datetime(created_at)
        if parsed_occurred is None or parsed_created is None:
            return None
        return cls(occurred_at=parsed_occurred, created_at=parsed_created)

    def encode(self) -> str:
        return f"{self.occurred_at.isoformat()}{SEPARATOR}{self.created_at.isoformat()}"
