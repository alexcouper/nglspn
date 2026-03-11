from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from services import REPO

from .models import (
    BroadcastEmail,
    BroadcastEmailImage,
    BroadcastEmailRecipient,
    BroadcastEmailStatus,
    SentEmail,
)

if TYPE_CHECKING:
    from django.http import HttpRequest


class BroadcastEmailImageInline(admin.TabularInline):
    model = BroadcastEmailImage
    extra = 1
    fields = ("image", "thumbnail_preview")
    readonly_fields = ("thumbnail_preview",)

    @admin.display(description="Preview")
    def thumbnail_preview(self, obj: BroadcastEmailImage) -> str:
        if not obj.pk or not obj.image:
            return "Save to see preview"
        return format_html(
            '<div style="display:flex;align-items:center;gap:10px;">'
            '<img src="{}" style="max-height:80px;max-width:200px;'
            'border-radius:4px;" />'
            '<button type="button" class="broadcast-image-insert button" '
            'data-url="{}" data-filename="{}">Insert</button>'
            "</div>",
            obj.url,
            obj.url,
            obj.original_filename,
        )


class BroadcastEmailRecipientInline(admin.TabularInline):
    model = BroadcastEmailRecipient
    extra = 0
    readonly_fields = ("user", "sent_at", "success", "error_message")
    can_delete = False

    def has_add_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return False


@admin.register(BroadcastEmail)
class BroadcastEmailAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "email_type",
        "status_badge",
        "recipient_count",
        "created_by",
        "created_at",
    )
    list_filter = ("email_type", "sent_at")
    search_fields = ("subject",)
    autocomplete_fields = ("individual_recipients",)
    fieldsets = (
        (None, {"fields": ("subject", "body_markdown")}),
        (
            "Targeting",
            {
                "fields": ("email_type", "individual_recipients"),
                "description": (
                    "Choose an email type to send to all opted-in users, "
                    "or leave blank and select individual recipients."
                ),
            },
        ),
        (
            "Status",
            {
                "fields": ("status", "sent_at", "sent_by", "created_by"),
            },
        ),
    )

    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: BroadcastEmail | None = None,
    ) -> tuple[str, ...]:
        always_readonly = ("status", "sent_at", "sent_by", "created_by")
        if obj and obj.status != BroadcastEmailStatus.DRAFT:
            return (
                "subject",
                "body_markdown",
                "email_type",
                "individual_recipients",
                *always_readonly,
            )
        return always_readonly

    def get_inlines(
        self,
        request: HttpRequest,
        obj: BroadcastEmail | None = None,
    ) -> list[type]:
        if obj and obj.status != BroadcastEmailStatus.DRAFT:
            return [BroadcastEmailRecipientInline]
        if obj:
            return [BroadcastEmailImageInline]
        return []

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: BroadcastEmail | None = None,
    ) -> bool:
        if obj and obj.status != BroadcastEmailStatus.DRAFT:
            return False
        return super().has_delete_permission(request, obj)

    def save_model(
        self,
        request: HttpRequest,
        obj: BroadcastEmail,
        form: object,
        change: bool,  # noqa: FBT001
    ) -> None:
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Status")
    def status_badge(self, obj: BroadcastEmail) -> str:
        colors = {
            BroadcastEmailStatus.DRAFT: "#6b7280",
            BroadcastEmailStatus.QUEUED_FOR_SENDING: "#d97706",
            BroadcastEmailStatus.SENDING: "#2563eb",
            BroadcastEmailStatus.SENT: "#16a34a",
            BroadcastEmailStatus.FAILED: "#dc2626",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 8px;'
            'border-radius:4px;font-size:11px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description="Recipients")
    def recipient_count(self, obj: BroadcastEmail) -> int:
        if obj.is_sent:
            return obj.delivery_records.count()
        return REPO.email.resolve_broadcast_recipients(obj).count()

    def get_urls(self) -> list:
        custom_urls = [
            path(
                "<uuid:pk>/preview/",
                self.admin_site.admin_view(self.preview_view),
                name="emails_broadcastemail_preview",
            ),
            path(
                "<uuid:pk>/send/",
                self.admin_site.admin_view(self.send_view),
                name="emails_broadcastemail_send",
            ),
        ]
        return custom_urls + super().get_urls()

    def preview_view(self, request: HttpRequest, pk: str) -> HttpResponse:
        broadcast = get_object_or_404(BroadcastEmail, pk=pk)
        html, text = REPO.email.render_broadcast_email(broadcast)

        if request.GET.get("format") == "text":
            return HttpResponse(
                f"<pre style='max-width:600px;margin:40px auto;"
                f"font-family:monospace;white-space:pre-wrap;'>{text}</pre>",
                content_type="text/html",
            )
        return HttpResponse(html)

    def send_view(self, request: HttpRequest, pk: str) -> HttpResponse:
        from api.tasks.email import send_broadcast_email  # noqa: PLC0415

        broadcast = get_object_or_404(BroadcastEmail, pk=pk)
        change_url = reverse(
            "admin:emails_broadcastemail_change",
            args=[broadcast.pk],
        )

        if broadcast.status != BroadcastEmailStatus.DRAFT:
            messages.error(request, "This email can only be sent from draft status.")
            return redirect(change_url)

        recipients = REPO.email.resolve_broadcast_recipients(broadcast)
        recipient_count = recipients.count()

        if recipient_count == 0:
            messages.error(request, "No recipients found for this email.")
            return redirect(change_url)

        if request.method == "POST":
            broadcast.status = BroadcastEmailStatus.QUEUED_FOR_SENDING
            broadcast.save(update_fields=["status"])
            send_broadcast_email.enqueue(str(broadcast.pk), str(request.user.pk))
            messages.success(
                request,
                f"Email to {recipient_count} recipient(s) has been queued for sending.",
            )
            return redirect(change_url)

        context = {
            **self.admin_site.each_context(request),
            "broadcast": broadcast,
            "recipient_count": recipient_count,
            "opts": self.model._meta,  # noqa: SLF001
        }
        return render(
            request,
            "admin/emails/broadcastemail/send_confirm.html",
            context,
        )

    def change_view(
        self,
        request: HttpRequest,
        object_id: str,
        form_url: str = "",
        extra_context: dict | None = None,
    ) -> HttpResponse:
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj:
            extra_context["show_broadcast_buttons"] = (
                obj.status == BroadcastEmailStatus.DRAFT
            )
            extra_context["preview_url"] = reverse(
                "admin:emails_broadcastemail_preview",
                args=[obj.pk],
            )
            extra_context["send_url"] = reverse(
                "admin:emails_broadcastemail_send",
                args=[obj.pk],
            )
        return super().change_view(
            request,
            object_id,
            form_url,
            extra_context=extra_context,
        )


@admin.register(SentEmail)
class SentEmailAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "email_type",
        "to_email",
        "subject",
        "success",
        "preview_link",
    )
    list_filter = ("email_type", "success", "created_at")
    search_fields = ("to_email", "subject")
    readonly_fields = (
        "id",
        "recipient",
        "email_type",
        "subject",
        "to_email",
        "success",
        "error_message",
        "created_at",
        "preview_link",
    )
    exclude = ("html_body",)
    ordering = ("-created_at",)

    @admin.display(description="Preview")
    def preview_link(self, obj: SentEmail) -> str:
        if not obj.pk or not obj.html_body:
            return "-"
        url = reverse("admin:emails_sentemail_preview", args=[obj.pk])
        return format_html('<a href="{}" target="_blank">View</a>', url)

    def get_urls(self) -> list:
        custom_urls = [
            path(
                "<uuid:pk>/preview/",
                self.admin_site.admin_view(self.preview_view),
                name="emails_sentemail_preview",
            ),
        ]
        return custom_urls + super().get_urls()

    def preview_view(self, request: HttpRequest, pk: str) -> HttpResponse:
        sent_email = get_object_or_404(SentEmail, pk=pk)
        if not sent_email.html_body:
            return HttpResponse(
                "<p>No HTML preview available for this email.</p>",
                content_type="text/html",
            )
        return HttpResponse(sent_email.html_body)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: SentEmail | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: SentEmail | None = None
    ) -> bool:
        return False
