from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.feed.admin import promote_discussions

from .models import Discussion


@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "author", "parent", "created_at")
    list_filter = ("created_at",)
    search_fields = ("body", "project__title", "author__email")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    actions = ("promote_to_feed",)

    @admin.action(description="Promote to the Latest feed")
    def promote_to_feed(
        self, request: HttpRequest, queryset: QuerySet[Discussion]
    ) -> None:
        promote_discussions(self, request, queryset)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Discussion]:
        return (
            super().get_queryset(request).select_related("project", "author", "parent")
        )
