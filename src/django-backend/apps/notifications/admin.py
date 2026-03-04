from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone

from services.email.django_impl import render_email
from services.email.django_impl.handler import build_digest_groups

from .models import Notification

if TYPE_CHECKING:
    from uuid import UUID

    from django.http import HttpRequest


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "recipient",
        "discussion",
        "cadence",
        "sent",
        "created_at",
        "sent_at",
    )
    list_filter = ("cadence", "sent", "created_at")
    search_fields = ("recipient__email",)
    readonly_fields = ("id", "created_at")
    ordering = ("-created_at",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Notification]:
        return super().get_queryset(request).select_related("recipient", "discussion")

    def get_urls(self) -> list:
        custom_urls = [
            path(
                "preview-digest/",
                self.admin_site.admin_view(self.preview_digest_list_view),
                name="notifications_notification_preview_digest",
            ),
            path(
                "preview-digest/<uuid:recipient_id>/",
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
        unsent = (
            Notification.objects.filter(sent=False)
            .select_related(
                "recipient",
                "discussion",
                "discussion__project",
                "discussion__author",
            )
            .order_by("recipient_id", "created_at")
        )

        by_recipient: defaultdict[UUID, dict] = defaultdict(
            lambda: {"recipient": None, "projects": defaultdict(int), "count": 0}
        )
        for n in unsent:
            entry = by_recipient[n.recipient_id]
            entry["recipient"] = n.recipient
            entry["projects"][n.discussion.project.title] += 1
            entry["count"] += 1

        recipients_data = []
        for recipient_id, data in sorted(
            by_recipient.items(), key=lambda x: x[1]["count"], reverse=True
        ):
            recipients_data.append(
                {
                    "recipient": data["recipient"],
                    "count": data["count"],
                    "projects": dict(data["projects"]),
                    "preview_url": reverse(
                        "admin:notifications_notification_preview_digest_detail",
                        args=[recipient_id],
                    ),
                }
            )

        context = {
            **self.admin_site.each_context(request),
            "recipients": recipients_data,
            "total_unsent": unsent.count(),
            "opts": self.model._meta,  # noqa: SLF001
        }
        return render(
            request,
            "admin/notifications/notification/preview_digest_list.html",
            context,
        )

    def preview_digest_detail_view(
        self, request: HttpRequest, recipient_id: str
    ) -> HttpResponse:
        unsent = (
            Notification.objects.filter(recipient_id=recipient_id, sent=False)
            .select_related(
                "recipient",
                "discussion",
                "discussion__project",
                "discussion__author",
            )
            .order_by("created_at")
        )

        notifications = list(unsent)
        if not notifications:
            return HttpResponse(
                "<p>No unsent notifications for this recipient.</p>",
                content_type="text/html",
            )

        recipient = notifications[0].recipient

        context = {
            "recipient_name": recipient.first_name or "there",
            "groups": build_digest_groups(notifications),
            "site_url": settings.FRONTEND_URL,
            "logo_url": f"{settings.S3_PUBLIC_URL_BASE}/email/logo.png",
            "current_year": timezone.now().year,
        }
        html, _text = render_email("discussion_digest", context)

        if request.GET.get("format") == "text":
            return HttpResponse(
                f"<pre style='max-width:600px;margin:40px auto;"
                f"font-family:monospace;white-space:pre-wrap;'>{_text}</pre>",
                content_type="text/html",
            )
        return HttpResponse(html)
