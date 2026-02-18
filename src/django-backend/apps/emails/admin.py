from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from svc import HANDLERS, REPO

from .models import BroadcastEmail, BroadcastEmailImage, BroadcastEmailRecipient

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
                "fields": ("sent_at", "sent_by", "created_by"),
            },
        ),
    )

    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: BroadcastEmail | None = None,
    ) -> tuple[str, ...]:
        always_readonly = ("sent_at", "sent_by", "created_by")
        if obj and obj.is_sent:
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
        if obj and obj.is_sent:
            return [BroadcastEmailRecipientInline]
        if obj:
            return [BroadcastEmailImageInline]
        return []

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: BroadcastEmail | None = None,
    ) -> bool:
        if obj and obj.is_sent:
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
        if obj.is_sent:
            return format_html(
                '<span style="background:{};color:#fff;padding:3px 8px;'
                'border-radius:4px;font-size:11px;">{}</span>',
                "#16a34a",
                "Sent",
            )
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 8px;'
            'border-radius:4px;font-size:11px;">{}</span>',
            "#6b7280",
            "Draft",
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
        broadcast = get_object_or_404(BroadcastEmail, pk=pk)

        if broadcast.is_sent:
            messages.error(request, "This email has already been sent.")
            return redirect(
                reverse(
                    "admin:emails_broadcastemail_change",
                    args=[broadcast.pk],
                )
            )

        recipients = REPO.email.resolve_broadcast_recipients(broadcast)
        recipient_count = recipients.count()

        if recipient_count == 0:
            messages.error(request, "No recipients found for this email.")
            return redirect(
                reverse(
                    "admin:emails_broadcastemail_change",
                    args=[broadcast.pk],
                )
            )

        if request.method == "POST":
            success_count, failure_count = HANDLERS.email.send_broadcast(
                broadcast, request.user
            )
            messages.success(
                request,
                f"Email sent to {success_count} recipient(s)"
                + (f" ({failure_count} failed)" if failure_count else "")
                + ".",
            )
            return redirect(
                reverse(
                    "admin:emails_broadcastemail_change",
                    args=[broadcast.pk],
                )
            )

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
            extra_context["show_broadcast_buttons"] = not obj.is_sent
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
