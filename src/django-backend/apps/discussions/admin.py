from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import Discussion


@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "author", "parent", "created_at")
    list_filter = ("created_at",)
    search_fields = ("body", "project__title", "author__email")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Discussion]:
        return (
            super().get_queryset(request).select_related("project", "author", "parent")
        )
