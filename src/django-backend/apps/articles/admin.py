from django.conf import settings
from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html

from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "project",
        "channel",
        "author",
        "source",
        "state",
        "global_visibility",
        "published_at",
    )
    list_filter = ("state", "source", "global_visibility", "created_at")
    search_fields = ("title", "body", "project__title", "author__email")
    readonly_fields = (
        "id",
        "slug",
        "created_at",
        "updated_at",
        "render_link",
    )
    ordering = ("-published_at", "-created_at")
    autocomplete_fields = (
        "project",
        "channel",
        "author",
        "listing_image",
        "about_feed_event",
    )

    fieldsets = (
        (None, {"fields": ("id", "project", "channel", "author")}),
        ("Content", {"fields": ("title", "slug", "body", "listing_image")}),
        (
            "Source",
            {"fields": ("source", "external_url")},
        ),
        (
            "Lifecycle",
            {
                "fields": (
                    "state",
                    "published_at",
                    "global_visibility",
                ),
            },
        ),
        (
            "Latest feed",
            {
                "fields": ("about_feed_event",),
                "description": (
                    "The platform event this article is a write-up of. Setting "
                    "it retires the bare event so the feed shows one entry "
                    "instead of two. Only takes effect while that event has "
                    "not already been superseded."
                ),
            },
        ),
        ("Render", {"fields": ("render_link",)}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Article]:
        return (
            super()
            .get_queryset(request)
            .select_related("project", "channel", "author", "listing_image")
        )

    @admin.display(description="Render page")
    def render_link(self, obj: Article) -> str:
        if not obj.slug or obj.state != "published":
            return "—"
        url = f"{settings.FRONTEND_URL}/projects/{obj.project.slug}/articles/{obj.slug}"
        return format_html('<a href="{}" target="_blank">{}</a>', url, url)
