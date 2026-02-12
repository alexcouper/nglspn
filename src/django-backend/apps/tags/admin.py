from __future__ import annotations

from typing import TYPE_CHECKING

from django import forms
from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils import timezone
from django.utils.html import format_html

from .models import Tag, TagCategory, TagStatus

if TYPE_CHECKING:
    from django.utils.safestring import SafeString


class ColorPickerWidget(forms.TextInput):
    input_type = "color"

    def format_value(self, value: str | None) -> str:
        # Return a default color if empty, since color input requires a value
        return value if value else "#808080"


class TagAdminForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = [
            "name",
            "slug",
            "description",
            "color",
            "category",
            "status",
            "created_by",
        ]
        widgets = {
            "color": ColorPickerWidget(attrs={"style": "width: 60px; height: 30px;"}),
        }


@admin.register(TagCategory)
class TagCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "display_order", "tag_count", "is_active")
    list_filter = ("is_active",)
    list_editable = ("display_order", "is_active")
    search_fields = ("name", "slug", "description")
    ordering = ("display_order", "name")
    readonly_fields = ("id", "created_at", "updated_at")
    prepopulated_fields = {"slug": ("name",)}

    fieldsets = (
        ("Category Information", {"fields": ("name", "slug", "description")}),
        ("Settings", {"fields": ("display_order", "is_active")}),
        (
            "System",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    @admin.display(description="Tags")
    def tag_count(self, obj: TagCategory) -> int:
        return obj.tags.count()

    def get_queryset(self, request: HttpRequest) -> QuerySet[TagCategory]:
        return super().get_queryset(request).prefetch_related("tags")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    form = TagAdminForm
    list_display = (
        "name",
        "slug",
        "category",
        "color_display",
        "status_display",
        "project_count",
        "created_at",
    )
    list_filter = ("status", "category", "created_at")
    search_fields = ("name", "slug", "description")
    ordering = ("name",)
    readonly_fields = ("id", "created_at", "updated_at", "reviewed_at", "reviewed_by")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("category", "created_by")
    actions = ["approve_tags", "reject_tags"]

    fieldsets = (
        (
            "Tag Information",
            {"fields": ("name", "slug", "description", "color", "category")},
        ),
        (
            "Status",
            {
                "fields": (
                    "status",
                    "created_by",
                    "reviewed_by",
                    "reviewed_at",
                )
            },
        ),
        (
            "System",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    @admin.display(description="Color")
    def color_display(self, obj: Tag) -> SafeString | str:
        if obj.color:
            return format_html(
                '<span style="background-color: {}; color: white; '
                'padding: 2px 6px; border-radius: 3px;">{}</span>',
                obj.color,
                obj.color,
            )
        return "-"

    @admin.display(description="Status")
    def status_display(self, obj: Tag) -> SafeString:
        colors = {
            TagStatus.PENDING: "#ffc107",
            TagStatus.APPROVED: "#28a745",
            TagStatus.REJECTED: "#dc3545",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 6px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description="Projects")
    def project_count(self, obj: Tag) -> int:
        return obj.projects.count()

    def get_queryset(self, request: HttpRequest) -> QuerySet[Tag]:
        return (
            super()
            .get_queryset(request)
            .select_related("category", "created_by", "reviewed_by")
            .prefetch_related("projects")
        )

    @admin.action(description="Approve selected tags")
    def approve_tags(self, request: HttpRequest, queryset: QuerySet[Tag]) -> None:
        updated = queryset.filter(status=TagStatus.PENDING).update(
            status=TagStatus.APPROVED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(
            request,
            f"{updated} tag(s) approved.",
            messages.SUCCESS,
        )

    @admin.action(description="Reject selected tags")
    def reject_tags(self, request: HttpRequest, queryset: QuerySet[Tag]) -> None:
        tags_to_reject = queryset.exclude(status=TagStatus.REJECTED)
        # Remove rejected tags from projects
        for tag in tags_to_reject:
            tag.projects.clear()
        updated = tags_to_reject.update(
            status=TagStatus.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(
            request,
            f"{updated} tag(s) rejected and removed from projects.",
            messages.SUCCESS,
        )
