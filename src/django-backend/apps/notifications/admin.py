from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib import admin
from django.db.models import QuerySet
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone

from services.email.django_impl import render_email
from services.email.django_impl.handler import (
    build_article_digest_entries,
    build_digest_groups,
)

from .models import Notification

if TYPE_CHECKING:
    from uuid import UUID

    from django.http import HttpRequest


DIGEST_KINDS = ("discussion", "article")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "recipient",
        "target",
        "email_cadence",
        "email_sent",
        "in_app_read_at",
        "created_at",
        "email_sent_at",
    )
    list_filter = ("email_cadence", "email_sent", "created_at")
    search_fields = ("recipient__email",)
    readonly_fields = ("id", "created_at")
    ordering = ("-created_at",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Notification]:
        return (
            super()
            .get_queryset(request)
            .select_related("recipient", "discussion", "article")
        )

    @admin.display(description="Target")
    def target(self, obj: Notification) -> str:
        if obj.discussion_id:
            return f"discussion: {obj.discussion}"
        if obj.article_id:
            return f"article: {obj.article}"
        return "—"

    def get_urls(self) -> list:
        custom_urls = [
            path(
                "preview-digest/",
                self.admin_site.admin_view(self.preview_digest_list_view),
                name="notifications_notification_preview_digest",
            ),
            path(
                "preview-digest/<str:kind>/<uuid:recipient_id>/",
                self.admin_site.admin_view(self.preview_digest_detail_view),
                name="notifications_notification_preview_digest_detail",
            ),
        ]
        return custom_urls + super().get_urls()

    def changelist_view(
        self,
        request: HttpRequest,
        extra_context: dict | None = None,
    ) -> HttpResponse:
        extra_context = extra_context or {}
        extra_context["preview_digest_url"] = reverse(
            "admin:notifications_notification_preview_digest"
        )
        return super().changelist_view(request, extra_context=extra_context)

    def preview_digest_list_view(self, request: HttpRequest) -> HttpResponse:
        discussion_unsent = (
            Notification.objects.filter(email_sent=False, discussion__isnull=False)
            .select_related(
                "recipient",
                "discussion",
                "discussion__project",
                "discussion__author",
            )
            .order_by("recipient_id", "created_at")
        )
        article_unsent = (
            Notification.objects.filter(email_sent=False, article__isnull=False)
            .select_related(
                "recipient",
                "article",
                "article__project",
                "article__channel",
            )
            .order_by("recipient_id", "created_at")
        )

        by_recipient: defaultdict[UUID, dict] = defaultdict(
            lambda: {
                "recipient": None,
                "discussion_projects": defaultdict(int),
                "article_projects": defaultdict(int),
                "discussion_count": 0,
                "article_count": 0,
            }
        )
        for n in discussion_unsent:
            entry = by_recipient[n.recipient_id]
            entry["recipient"] = n.recipient
            entry["discussion_projects"][n.discussion.project.title] += 1
            entry["discussion_count"] += 1
        for n in article_unsent:
            entry = by_recipient[n.recipient_id]
            entry["recipient"] = n.recipient
            entry["article_projects"][n.article.project.title] += 1
            entry["article_count"] += 1

        recipients_data = []
        for recipient_id, data in sorted(
            by_recipient.items(),
            key=lambda x: x[1]["discussion_count"] + x[1]["article_count"],
            reverse=True,
        ):
            recipients_data.append(
                {
                    "recipient": data["recipient"],
                    "discussion_count": data["discussion_count"],
                    "article_count": data["article_count"],
                    "discussion_projects": dict(data["discussion_projects"]),
                    "article_projects": dict(data["article_projects"]),
                    "discussion_preview_url": (
                        reverse(
                            "admin:notifications_notification_preview_digest_detail",
                            args=["discussion", recipient_id],
                        )
                        if data["discussion_count"]
                        else ""
                    ),
                    "article_preview_url": (
                        reverse(
                            "admin:notifications_notification_preview_digest_detail",
                            args=["article", recipient_id],
                        )
                        if data["article_count"]
                        else ""
                    ),
                }
            )

        context = {
            **self.admin_site.each_context(request),
            "recipients": recipients_data,
            "total_unsent": discussion_unsent.count() + article_unsent.count(),
            "opts": self.model._meta,  # noqa: SLF001
        }
        return render(
            request,
            "admin/notifications/notification/preview_digest_list.html",
            context,
        )

    def preview_digest_detail_view(
        self, request: HttpRequest, kind: str, recipient_id: str
    ) -> HttpResponse:
        if kind not in DIGEST_KINDS:
            raise Http404

        if kind == "discussion":
            notifications = list(
                Notification.objects.filter(
                    recipient_id=recipient_id,
                    email_sent=False,
                    discussion__isnull=False,
                )
                .select_related(
                    "recipient",
                    "discussion",
                    "discussion__project",
                    "discussion__author",
                )
                .order_by("created_at")
            )
        else:
            notifications = list(
                Notification.objects.filter(
                    recipient_id=recipient_id,
                    email_sent=False,
                    article__isnull=False,
                )
                .select_related(
                    "recipient",
                    "article",
                    "article__project",
                    "article__channel",
                )
                .order_by("created_at")
            )

        if not notifications:
            return HttpResponse(
                f"<p>No unsent {kind} notifications for this recipient.</p>",
                content_type="text/html",
            )

        recipient = notifications[0].recipient
        base_context = {
            "recipient_name": recipient.first_name or "there",
            "site_url": settings.FRONTEND_URL,
            "profile_url": f"{settings.FRONTEND_URL}/profile",
            "logo_url": f"{settings.S3_PUBLIC_URL_BASE}/email/logo.png",
            "current_year": timezone.now().year,
        }

        if kind == "discussion":
            context = {**base_context, "groups": build_digest_groups(notifications)}
            template_name = "discussion_digest"
        else:
            context = {
                **base_context,
                "entries": build_article_digest_entries(notifications),
            }
            template_name = "article_digest"

        html, text = render_email(template_name, context)

        if request.GET.get("format") == "text":
            return HttpResponse(
                f"<pre style='max-width:600px;margin:40px auto;"
                f"font-family:monospace;white-space:pre-wrap;'>{text}</pre>",
                content_type="text/html",
            )
        return HttpResponse(html)
