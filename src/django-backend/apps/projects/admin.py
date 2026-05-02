from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from django.contrib import admin, messages
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from api.tasks import email as email_tasks
from apps.users.models import User
from services import HANDLERS

from .models import (
    Competition,
    CompetitionReviewer,
    ImageVariant,
    Project,
    ProjectCategory,
    ProjectContributor,
    ProjectImage,
    ProjectRanking,
    ProjectStatus,
    ProjectView,
    ReviewStatus,
)

if TYPE_CHECKING:
    from django.utils.safestring import SafeString

logger = logging.getLogger(__name__)


@admin.register(ProjectCategory)
class ProjectCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "display_order", "project_count")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("display_order", "name")

    @admin.display(description="Projects")
    def project_count(self, obj: ProjectCategory) -> int:
        return obj.project_count

    def get_queryset(self, request: HttpRequest) -> QuerySet[ProjectCategory]:
        return (
            super()
            .get_queryset(request)
            .annotate(
                project_count=Count(
                    "projects",
                    filter=Q(projects__status="approved"),
                )
            )
        )


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 0
    readonly_fields = (
        "thumbnail",
        "original_filename",
        "is_main",
        "is_icon",
        "is_hero",
        "is_usage",
        "upload_status",
        "file_size_display",
        "created_at",
    )
    fields = (
        "thumbnail",
        "original_filename",
        "is_main",
        "is_icon",
        "is_hero",
        "is_usage",
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
        "creator_link",
        "creator_promo_opt_in",
        "is_community_tipoff",
        "status",
        "is_featured",
        "category",
        "view_count",
        "submission_month",
        "created_at",
    )
    list_filter = (
        "status",
        "is_community_tipoff",
        "is_featured",
        "category",
        "creator__opt_in_to_external_promotions",
        "submission_month",
        "created_at",
        "tags",
    )
    search_fields = ("title", "description", "creator__email", "creator__username")
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "view_count",
        "created_at",
        "updated_at",
        "approved_at",
        "is_community_tipoff",
    )
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
                    "category",
                    "is_featured",
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
                ),
            },
        ),
        ("Metrics", {"fields": ("view_count", "submission_month")}),
        ("Ownership", {"fields": ("creator", "is_community_tipoff")}),
        (
            "System",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    @admin.display(description="Creator", ordering="creator__email")
    def creator_link(self, obj: Project) -> SafeString | str:
        if obj.creator:
            url = reverse("admin:users_user_change", args=[obj.creator.pk])
            return format_html('<a href="{}">{}</a>', url, obj.creator.email)
        return "-"

    @admin.display(
        description="Promo opt-in",
        boolean=True,
        ordering="creator__opt_in_to_external_promotions",
    )
    def creator_promo_opt_in(self, obj: Project) -> bool | None:
        if obj.creator:
            return obj.creator.opt_in_to_external_promotions
        return None

    @admin.display(description="Total Views")
    def view_count(self, obj: Project) -> int:
        return obj.views.count()

    def get_queryset(self, request: HttpRequest) -> QuerySet[Project]:
        return (
            super()
            .get_queryset(request)
            .select_related("creator", "approved_by")
            .prefetch_related("tags", "views")
        )

    def save_model(
        self,
        request: HttpRequest,
        obj: Project,
        form: Any,
        change: bool,  # noqa: FBT001
    ) -> None:
        if change and obj.status == ProjectStatus.APPROVED and not obj.approved_at:
            obj.approved_at = timezone.now()
            obj.approved_by = request.user
        super().save_model(request, obj, form, change)

    list_editable = ("is_featured",)

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
            queryset.filter(status=ProjectStatus.PENDING).select_related("creator")
        )
        updated = queryset.filter(status=ProjectStatus.PENDING).update(
            status=ProjectStatus.APPROVED,
            approved_by=request.user,
            approved_at=timezone.now(),
        )
        for project in pending:
            try:
                email_tasks.send_project_approved_email.enqueue(str(project.id))
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
        updated = queryset.filter(is_featured=False).update(is_featured=True)
        self.message_user(request, f"{updated} projects were featured.")

    @admin.action(description="Unfeature selected projects")
    def unfeature_projects(
        self,
        request: HttpRequest,
        queryset: QuerySet[Project],
    ) -> None:
        updated = queryset.filter(is_featured=True).update(is_featured=False)
        self.message_user(request, f"{updated} projects were unfeatured.")


@admin.register(ProjectContributor)
class ProjectContributorAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "role", "full_edit", "created_at")
    list_filter = ("role", "full_edit", "created_at")
    search_fields = ("project__title", "user__email")
    autocomplete_fields = ("project", "user")
    readonly_fields = ("id", "created_at")
    ordering = ("project", "role", "created_at")


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


class ImageVariantInline(admin.TabularInline):
    model = ImageVariant
    extra = 0
    fields = ("size", "width", "height", "file_size", "storage_key", "created_at")
    readonly_fields = fields

    def has_add_permission(
        self,
        request: HttpRequest,
        obj: ProjectImage | None = None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: ProjectImage | None = None,
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
        "variant_count",
        "created_at",
    )
    list_filter = ("is_main", "upload_status", "content_type", "created_at")
    search_fields = ("original_filename", "project__title", "project__creator__email")
    ordering = ("-created_at",)
    inlines = (ImageVariantInline,)
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
            {
                "fields": (
                    "project",
                    "is_main",
                    "is_icon",
                    "is_hero",
                    "is_usage",
                    "display_order",
                ),
            },
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

    @admin.display(description="Variants", ordering="variant_count")
    def variant_count(self, obj: ProjectImage) -> int:
        return obj.variant_count

    def get_queryset(self, request: HttpRequest) -> QuerySet[ProjectImage]:
        return (
            super()
            .get_queryset(request)
            .select_related("project", "project__creator")
            .annotate(variant_count=Count("variants"))
        )


class CompetitionReviewerInline(admin.TabularInline):
    model = CompetitionReviewer
    extra = 1
    autocomplete_fields = ("user",)


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    change_form_template = "admin/competition_change_form.html"
    list_display = (
        "thumbnail",
        "name",
        "start_date",
        "submission_deadline",
        "winner_name",
        "project_count",
        "reviewer_count",
    )
    list_filter = ("start_date", "submission_deadline")
    search_fields = ("name",)
    filter_horizontal = ("projects",)
    autocomplete_fields = ("winner",)
    inlines = [CompetitionReviewerInline]
    ordering = ("-start_date",)
    actions = ("end_review_period",)
    readonly_fields = (
        "image_preview",
        "image_wide_preview",
        "image_wide_winner_preview",
    )

    fieldsets = (
        (
            None,
            {"fields": ("name", "slug", "image", "image_preview", "quote")},
        ),
        (
            "Wide Images",
            {
                "fields": (
                    "image_wide",
                    "image_wide_preview",
                    "image_wide_winner",
                    "image_wide_winner_preview",
                ),
            },
        ),
        (
            "Dates & Prize",
            {
                "fields": (
                    "start_date",
                    "submission_deadline",
                    "voting_end_date",
                    "prize_amount",
                ),
            },
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

    @admin.display(description="Wide Image Preview")
    def image_wide_preview(self, obj: Competition) -> SafeString:
        if obj.image_wide:
            return format_html(
                '<img src="{}" style="max-height: 200px; max-width: 600px;" />',
                obj.image_wide.url,
            )
        return mark_safe('<span style="color: #999;">No wide image uploaded</span>')

    @admin.display(description="Wide Winner Image Preview")
    def image_wide_winner_preview(self, obj: Competition) -> SafeString:
        if obj.image_wide_winner:
            return format_html(
                '<img src="{}" style="max-height: 200px; max-width: 600px;" />',
                obj.image_wide_winner.url,
            )
        return mark_safe(
            '<span style="color: #999;">No wide winner image uploaded</span>'
        )

    @admin.display(description="Winner", ordering="winner__title")
    def winner_name(self, obj: Competition) -> str:
        return obj.winner.title if obj.winner else "-"

    @admin.display(description="Projects")
    def project_count(self, obj: Competition) -> int:
        return obj.projects.count()

    @admin.display(description="Reviewers")
    def reviewer_count(self, obj: Competition) -> int:
        return obj.reviewers.count()

    @admin.action(description="End review period for selected competitions")
    def end_review_period(
        self,
        request: HttpRequest,
        queryset: QuerySet[Competition],
    ) -> None:
        total_ended = 0
        competition_count = queryset.count()
        for competition in queryset:
            total_ended += HANDLERS.reviews.end_review_period(competition.id)
        self.message_user(
            request,
            f"Ended review period for {competition_count} competition(s); "
            f"{total_ended} review(s) marked as ended.",
        )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Competition]:
        return super().get_queryset(request).select_related("winner")

    def response_change(self, request: HttpRequest, obj: Competition) -> HttpResponse:
        if "_add_all_reviewers" in request.POST:
            existing_user_ids = CompetitionReviewer.objects.filter(
                competition=obj,
            ).values_list("user_id", flat=True)
            new_users = User.objects.filter(is_active=True).exclude(
                id__in=existing_user_ids,
            )
            reviewers = [
                CompetitionReviewer(user=user, competition=obj) for user in new_users
            ]
            CompetitionReviewer.objects.bulk_create(reviewers)
            already = len(existing_user_ids)
            added = len(reviewers)
            self.message_user(
                request,
                f"Added {added} users as reviewers ({already} already assigned).",
                messages.SUCCESS,
            )
            return self.response_post_save_change(request, obj)
        return super().response_change(request, obj)

    def get_urls(self) -> list:
        custom_urls = [
            path(
                "<uuid:pk>/voting-results/",
                self.admin_site.admin_view(self.voting_results_view),
                name="projects_competition_voting_results",
            ),
        ]
        return custom_urls + super().get_urls()

    def change_view(
        self,
        request: HttpRequest,
        object_id: str,
        form_url: str = "",
        extra_context: dict[str, Any] | None = None,
    ) -> HttpResponse:
        extra_context = extra_context or {}
        extra_context["voting_results_url"] = reverse(
            "admin:projects_competition_voting_results",
            args=[object_id],
        )
        return super().change_view(request, object_id, form_url, extra_context)

    def voting_results_view(self, request: HttpRequest, pk: str) -> HttpResponse:
        competition = get_object_or_404(Competition, pk=pk)

        completed_reviewer_ids = CompetitionReviewer.objects.filter(
            competition=competition,
            status=ReviewStatus.COMPLETED,
        ).values_list("user_id", flat=True)

        total_voters = len(completed_reviewer_ids)

        projects = competition.projects.exclude(
            status__in=[ProjectStatus.REJECTED, ProjectStatus.ICE_BOX],
        )
        total_projects = projects.count()

        project_data: dict[Any, dict] = {}
        for project in projects:
            project_data[project.id] = {
                "project": project,
                "total_score": 0,
                "position_counts": defaultdict(int),
            }

        rankings = ProjectRanking.objects.filter(
            competition=competition,
            reviewer_id__in=completed_reviewer_ids,
        ).select_related("project")

        for ranking in rankings:
            pid = ranking.project_id
            if pid not in project_data:
                continue
            score = total_projects - ranking.position + 1
            project_data[pid]["total_score"] += score
            project_data[pid]["position_counts"][ranking.position] += 1

        results = sorted(
            project_data.values(),
            key=lambda x: (
                -x["total_score"],
                -x["position_counts"].get(1, 0),
            ),
        )

        rank = 1
        for i, row in enumerate(results):
            if i > 0 and row["total_score"] < results[i - 1]["total_score"]:
                rank = i + 1
            row["rank"] = rank

        positions = list(range(1, total_projects + 1))
        position_headers = [_ordinal(p) for p in positions]
        for row in results:
            row["position_list"] = [row["position_counts"].get(p, 0) for p in positions]

        context = {
            **self.admin_site.each_context(request),
            "competition": competition,
            "results": results,
            "positions": positions,
            "position_headers": position_headers,
            "total_voters": total_voters,
            "total_projects": total_projects,
            "opts": self.model._meta,  # noqa: SLF001
            "title": f"Voting Results: {competition.name}",
        }
        return render(
            request,
            "admin/projects/competition/voting_results.html",
            context,
        )


_TEEN_RANGE = range(11, 14)
_ORDINAL_SUFFIXES = {1: "st", 2: "nd", 3: "rd"}


def _ordinal(n: int) -> str:
    suffix = "th" if n % 100 in _TEEN_RANGE else _ORDINAL_SUFFIXES.get(n % 10, "th")
    return f"{n}{suffix}"


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
