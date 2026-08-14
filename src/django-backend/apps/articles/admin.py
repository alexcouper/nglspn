from django.conf import settings
from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html

from services import HANDLERS

from .models import Article, ArticleGlobalVisibility


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
        # Both are set by the service layer and neither is safe to type in.
        # Approving is what notifies an article's followers, and the form saves
        # the model directly — editing the field here would flip the article
        # visible and tell nobody. The actions below are the way in.
        "global_visibility",
        "approved_at",
    )
    ordering = ("-published_at", "-created_at")
    actions = ("approve_articles", "demote_articles")
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
                    "approved_at",
                ),
                "description": (
                    "Visibility is changed with the Approve and Demote actions "
                    "on the article list, not here — approving is what "
                    "notifies the article's followers. Approved is when the "
                    "article became visible to everyone, which is what decides "
                    "whether it is still fresh enough to notify anyone about; "
                    "an import that should notify nobody wants it backdated."
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

    @admin.action(description="Approve (show to everyone, notify followers)")
    def approve_articles(
        self, request: HttpRequest, queryset: QuerySet[Article]
    ) -> None:
        self._set_visibility(request, queryset, ArticleGlobalVisibility.APPROVED)

    @admin.action(description="Demote (hide from everyone)")
    def demote_articles(
        self, request: HttpRequest, queryset: QuerySet[Article]
    ) -> None:
        self._set_visibility(request, queryset, ArticleGlobalVisibility.DEMOTED)

    def _set_visibility(
        self, request: HttpRequest, queryset: QuerySet[Article], value: str
    ) -> None:
        # Through the handler, not queryset.update(): approving stamps
        # approved_at, enqueues the fan-out and re-runs the feed's supersession
        # link, none of which a bulk write would do.
        changed = 0
        for article in queryset:
            if article.global_visibility == value:
                continue
            HANDLERS.articles.set_global_visibility(article.id, value)
            changed += 1
        self.message_user(request, f"Updated {changed} articles.")

    @admin.display(description="Render page")
    def render_link(self, obj: Article) -> str:
        if not obj.slug or obj.state != "published":
            return "—"
        url = f"{settings.FRONTEND_URL}/projects/{obj.project.slug}/articles/{obj.slug}"
        return format_html('<a href="{}" target="_blank">{}</a>', url, url)
