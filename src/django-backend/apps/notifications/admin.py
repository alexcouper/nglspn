from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import Notification


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
