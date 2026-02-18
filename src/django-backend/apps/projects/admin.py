from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from svc import HANDLERS

from .models import (
    Competition,
    CompetitionReviewer,
    Project,
    ProjectImage,
    ProjectRanking,
    ProjectStatus,
    ProjectView,
)

if TYPE_CHECKING:
    from django.utils.safestring import SafeString

logger = logging.getLogger(__name__)


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 0
    readonly_fields = (
        "thumbnail",
        "original_filename",
        "is_main",
        "upload_status",
        "file_size_display",
        "created_at",
    )
    fields = (
        "thumbnail",
        "original_filename",
        "is_main",
        "upload_status",
        "file_size_display",
        "created_at",
    )
    can_delete = True
    ordering = ("display_order",)

    @admin.display(description="Preview")
    def thumbnail(self, obj: ProjectImage) -> SafeString:
        return format_html(
            '<img src="{}" style="max-height: 50px; max-width: 100px;" />',
            obj.url,
        )

    @admin.display(description="Size")
    def file_size_display(self, obj: ProjectImage) -> str:
        kb = 1024
        mb = kb * kb
        if obj.file_size < kb:
            return f"{obj.file_size} B"
        if obj.file_size < mb:
            return f"{obj.file_size / kb:.1f} KB"
        return f"{obj.file_size / mb:.1f} MB"

    def has_add_permission(
        self,
        request: HttpRequest,
        obj: Project | None = None,
    ) -> bool:
        return False


class ProjectViewInline(admin.TabularInline):
    model = ProjectView
    extra = 0
    readonly_fields = ("viewer_ip", "user_agent", "created_at")
    can_delete = False

    def has_add_permission(
        self,
        request: HttpRequest,
        obj: Project | None = None,
    ) -> bool:
        return False


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "owner_link",
        "status",
        "is_featured",
        "monthly_visitors",
        "view_count",
        "submission_month",
        "created_at",
    )
    list_filter = ("status", "is_featured", "submission_month", "created_at", "tags")
    search_fields = ("title", "description", "owner__email", "owner__username")
    ordering = ("-created_at",)
    readonly_fields = ("id", "view_count", "created_at", "updated_at", "approved_at")
    filter_horizontal = ("tags",)
    inlines = [ProjectImageInline, ProjectViewInline]

    fieldsets = (
        (
            "Project Information",
            {
                "fields": (
                    "title",
                    "description",
                    "long_description",
                    "tech_stack",
                    "tags",
                ),
            },
        ),
        (
            "URLs",
            {"fields": ("website_url", "github_url", "demo_url")},
        ),
        (
            "Status & Approval",
            {
                "fields": (
                    "status",
                    "rejection_reason",
                    "approved_by",
                    "approved_at",
                    "is_featured",
                ),
            },
        ),
        ("Metrics", {"fields": ("monthly_visitors", "view_count", "submission_month")}),
        ("Ownership", {"fields": ("owner",)}),
        (
            "System",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    @admin.display(description="Owner", ordering="owner__email")
    def owner_link(self, obj: Project) -> SafeString | str:
        if obj.owner:
            url = reverse("admin:users_user_change", args=[obj.owner.pk])
            return format_html('<a href="{}">{}</a>', url, obj.owner.email)
        return "-"

    @admin.display(description="Total Views")
    def view_count(self, obj: Project) -> int:
        return obj.views.count()

    def get_queryset(self, request: HttpRequest) -> QuerySet[Project]:
        return (
            super()
            .get_queryset(request)
            .select_related("owner", "approved_by")
            .prefetch_related("tags", "views")
        )

    actions = [
        "approve_projects",
        "reject_projects",
        "feature_projects",
        "unfeature_projects",
    ]

    @admin.action(description="Approve selected projects")
    def approve_projects(
        self,
        request: HttpRequest,
        queryset: QuerySet[Project],
    ) -> None:
        pending = list(
            queryset.filter(status=ProjectStatus.PENDING).select_related("owner")
        )
        updated = queryset.filter(status=ProjectStatus.PENDING).update(
            status=ProjectStatus.APPROVED,
            approved_by=request.user,
            approved_at=timezone.now(),
        )
        for project in pending:
            try:
                HANDLERS.email.send_project_approved_email(project)
            except Exception:
                logger.exception(
                    "Failed to send approval email for project %s", project.id
                )
        self.message_user(request, f"{updated} projects were approved.")

    @admin.action(description="Reject selected projects")
    def reject_projects(
        self,
        request: HttpRequest,
        queryset: QuerySet[Project],
    ) -> None:
        updated = queryset.filter(status=ProjectStatus.PENDING).update(
            status=ProjectStatus.REJECTED,
            approved_by=request.user,
        )
        self.message_user(request, f"{updated} projects were rejected.")

    @admin.action(description="Feature selected projects")
    def feature_projects(
        self,
        request: HttpRequest,
        queryset: QuerySet[Project],
    ) -> None:
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"{updated} projects were featured.")

    @admin.action(description="Unfeature selected projects")
    def unfeature_projects(
        self,
        request: HttpRequest,
        queryset: QuerySet[Project],
    ) -> None:
        updated = queryset.update(is_featured=False)
        self.message_user(request, f"{updated} projects were unfeatured.")


@admin.register(ProjectView)
class ProjectViewAdmin(admin.ModelAdmin):
    list_display = ("project_link", "viewer_ip", "created_at")
    list_filter = ("created_at",)
    search_fields = ("project__title", "viewer_ip")
    readonly_fields = ("id", "project", "viewer_ip", "user_agent", "created_at")
    ordering = ("-created_at",)

    @admin.display(description="Project", ordering="project__title")
    def project_link(self, obj: ProjectView) -> SafeString | str:
        if obj.project:
            url = reverse("admin:projects_project_change", args=[obj.project.pk])
            return format_html('<a href="{}">{}</a>', url, obj.project.title)
        return "-"

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: ProjectView | None = None,
    ) -> bool:
        return False


@admin.register(ProjectImage)
class ProjectImageAdmin(admin.ModelAdmin):
    list_display = (
        "thumbnail",
        "original_filename",
        "project_link",
        "is_main",
        "upload_status",
        "file_size_display",
        "dimensions",
        "created_at",
    )
    list_filter = ("is_main", "upload_status", "content_type", "created_at")
    search_fields = ("original_filename", "project__title", "project__owner__email")
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "thumbnail_large",
        "storage_key",
        "content_type",
        "file_size",
        "width",
        "height",
        "created_at",
        "uploaded_at",
    )

    fieldsets = (
        (
            "Image",
            {"fields": ("thumbnail_large", "original_filename", "storage_key")},
        ),
        (
            "Project",
            {"fields": ("project", "is_main", "display_order")},
        ),
        (
            "File Info",
            {"fields": ("content_type", "file_size", "width", "height")},
        ),
        (
            "Status",
            {"fields": ("upload_status", "created_at", "uploaded_at")},
        ),
        (
            "System",
            {"fields": ("id",), "classes": ("collapse",)},
        ),
    )

    @admin.display(description="Preview")
    def thumbnail(self, obj: ProjectImage) -> SafeString:
        return format_html(
            '<img src="{}" style="max-height: 50px; max-width: 80px;" />',
            obj.url,
        )

    @admin.display(description="Image Preview")
    def thumbnail_large(self, obj: ProjectImage) -> SafeString:
        return format_html(
            '<img src="{}" style="max-height: 300px; max-width: 500px;" />',
            obj.url,
        )

    @admin.display(description="Project", ordering="project__title")
    def project_link(self, obj: ProjectImage) -> SafeString | str:
        if obj.project:
            url = reverse("admin:projects_project_change", args=[obj.project.pk])
            title = obj.project.title or "Untitled"
            return format_html('<a href="{}">{}</a>', url, title)
        return "-"

    @admin.display(description="Size")
    def file_size_display(self, obj: ProjectImage) -> str:
        kb = 1024
        mb = kb * kb
        if obj.file_size < kb:
            return f"{obj.file_size} B"
        if obj.file_size < mb:
            return f"{obj.file_size / kb:.1f} KB"
        return f"{obj.file_size / mb:.1f} MB"

    @admin.display(description="Dimensions")
    def dimensions(self, obj: ProjectImage) -> str:
        if obj.width and obj.height:
            return f"{obj.width} x {obj.height}"
        return "-"

    def get_queryset(self, request: HttpRequest) -> QuerySet[ProjectImage]:
        return super().get_queryset(request).select_related("project", "project__owner")


class CompetitionReviewerInline(admin.TabularInline):
    model = CompetitionReviewer
    extra = 1
    autocomplete_fields = ("user",)


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = (
        "thumbnail",
        "name",
        "start_date",
        "end_date",
        "winner_name",
        "project_count",
        "reviewer_count",
    )
    list_filter = ("start_date", "end_date")
    search_fields = ("name",)
    filter_horizontal = ("projects",)
    autocomplete_fields = ("winner",)
    inlines = [CompetitionReviewerInline]
    ordering = ("-start_date",)
    readonly_fields = ("image_preview",)

    fieldsets = (
        (
            None,
            {"fields": ("name", "slug", "image", "image_preview", "quote")},
        ),
        (
            "Dates & Prize",
            {"fields": ("start_date", "end_date", "prize_amount")},
        ),
        (
            "Status",
            {"fields": ("status", "winner")},
        ),
        (
            "Projects",
            {"fields": ("projects",)},
        ),
    )

    @admin.display(description="Image")
    def thumbnail(self, obj: Competition) -> SafeString:
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 80px;" />',
                obj.image.url,
            )
        return mark_safe('<span style="color: #999;">No image</span>')

    @admin.display(description="Image Preview")
    def image_preview(self, obj: Competition) -> SafeString:
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 300px; max-width: 500px;" />',
                obj.image.url,
            )
        return mark_safe('<span style="color: #999;">No image uploaded</span>')

    @admin.display(description="Winner", ordering="winner__title")
    def winner_name(self, obj: Competition) -> str:
        return obj.winner.title if obj.winner else "-"

    @admin.display(description="Projects")
    def project_count(self, obj: Competition) -> int:
        return obj.projects.count()

    @admin.display(description="Reviewers")
    def reviewer_count(self, obj: Competition) -> int:
        return obj.reviewers.count()

    def get_queryset(self, request: HttpRequest) -> QuerySet[Competition]:
        return super().get_queryset(request).select_related("winner")


@admin.register(CompetitionReviewer)
class CompetitionReviewerAdmin(admin.ModelAdmin):
    list_display = ("user", "competition", "assigned_at")
    list_filter = ("competition", "assigned_at")
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "competition__name",
    )
    autocomplete_fields = ("user", "competition")
    ordering = ("-assigned_at",)


@admin.register(ProjectRanking)
class ProjectRankingAdmin(admin.ModelAdmin):
    list_display = ("reviewer", "competition", "project", "position", "updated_at")
    list_filter = ("competition", "reviewer")
    search_fields = (
        "reviewer__email",
        "project__title",
        "competition__name",
    )
    autocomplete_fields = ("reviewer", "competition", "project")
    ordering = ("competition", "reviewer", "position")
