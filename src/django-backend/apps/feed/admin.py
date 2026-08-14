from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.discussions.models import Discussion
from services import HANDLERS

from .models import FeedEvent


@admin.register(FeedEvent)
class FeedEventAdmin(admin.ModelAdmin):
    list_display = (
        "kind",
        "subject",
        "occurred_at",
        "is_pinned",
        "state",
    )
    list_filter = ("kind", "is_pinned", "occurred_at")
    search_fields = (
        "project__title",
        "competition__name",
        "article__title",
        "discussion__body",
    )
    readonly_fields = ("id", "kind", "occurred_at", "created_at", "superseded_by")
    ordering = ("-occurred_at",)
    autocomplete_fields = ("project", "competition", "article", "discussion")
    actions = ("pin_as_lead", "unpin", "retire_entries", "restore_entries")

    def get_queryset(self, request: HttpRequest) -> QuerySet[FeedEvent]:
        return super().get_queryset(request).with_sources()

    @admin.display(description="Subject")
    def subject(self, obj: FeedEvent) -> str:
        return obj.subject

    @admin.display(description="State")
    def state(self, obj: FeedEvent) -> str:
        if obj.superseded_by_id is not None:
            return "superseded"
        if obj.retired_at is not None:
            return "retired"
        return "live"

    @admin.action(description="Pin as the feed lead")
    def pin_as_lead(self, request: HttpRequest, queryset: QuerySet[FeedEvent]) -> None:
        events = list(queryset)
        if len(events) != 1:
            self.message_user(
                request,
                "Pick exactly one entry — there is only ever one lead.",
                level=messages.ERROR,
            )
            return
        HANDLERS.feed.set_pinned(events[0].id, pinned=True)
        self.message_user(request, "Pinned as the feed lead.")

    @admin.action(description="Unpin")
    def unpin(self, request: HttpRequest, queryset: QuerySet[FeedEvent]) -> None:
        for event in queryset:
            HANDLERS.feed.set_pinned(event.id, pinned=False)
        self.message_user(request, "Unpinned.")

    @admin.action(description="Retire (hide from the feed)")
    def retire_entries(
        self, request: HttpRequest, queryset: QuerySet[FeedEvent]
    ) -> None:
        for event in queryset:
            HANDLERS.feed.retire(event.id)
        self.message_user(request, f"Retired {queryset.count()} entries.")

    @admin.action(description="Restore to the feed")
    def restore_entries(
        self, request: HttpRequest, queryset: QuerySet[FeedEvent]
    ) -> None:
        for event in queryset:
            HANDLERS.feed.unretire(event.id)
        self.message_user(request, f"Restored {queryset.count()} entries.")


def promote_discussions(
    modeladmin: admin.ModelAdmin,
    request: HttpRequest,
    queryset: QuerySet[Discussion],
) -> None:
    """Push a thread into the Latest feed.

    Deliberately an action rather than an automatic source: discussion volume
    would drown three articles a week, so promotion is a decision someone makes.
    """
    promoted = 0
    for discussion in queryset:
        if discussion.parent_id is not None:
            continue
        HANDLERS.feed.promote_discussion(discussion)
        promoted += 1
    modeladmin.message_user(
        request,
        f"Promoted {promoted} threads to the feed."
        + (" Replies cannot be promoted." if promoted < queryset.count() else ""),
    )


promote_discussions.short_description = "Promote to the Latest feed"
