from datetime import timedelta
from math import ceil
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from django.db.models import Count, Prefetch, Q, QuerySet
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.projects.models import (
    Competition,
    Project,
    ProjectCategory,
    ProjectImage,
    ProjectStatus,
)
from services.project.exceptions import ProjectNotFoundError
from services.project.query_interface import (
    CategoryItem,
    DiscoverProjectItem,
    PaginatedProjects,
    ProjectListItem,
    ProjectQueryInterface,
    WinnerItem,
)

ALLOWED_SORT_FIELDS = {"created_at", "title", "updated_at"}


def _top_level_discussion_count() -> Count:
    return Count("discussions", filter=Q(discussions__parent__isnull=True))


def _discover_queryset() -> QuerySet[Project]:
    return Project.objects.select_related("owner", "category").prefetch_related(
        "won_competitions",
        Prefetch(
            "images",
            queryset=ProjectImage.objects.filter(
                upload_status="uploaded"
            ).prefetch_related("variants"),
        ),
    )


def _base_queryset() -> QuerySet[Project]:
    return Project.objects.select_related("owner").prefetch_related(
        "tags",
        "tags__category",
        "won_competitions",
        Prefetch(
            "images",
            queryset=ProjectImage.objects.filter(
                upload_status="uploaded"
            ).prefetch_related("variants"),
        ),
    )


def get_title_from_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    parsed_url = urlparse(url)
    domain = parsed_url.netloc or parsed_url.path

    domain = domain.replace("www.", "")
    if domain == "github.com":
        path_parts = parsed_url.path.strip("/").split("/")
        if len(path_parts) >= 2:  # noqa: PLR2004
            return path_parts[1]

    return domain or "Untitled Project"


def resolve_image_by_purpose(project: Project, purpose: str) -> "ProjectImage | None":
    """Fallback chain: purpose-specific image -> main image -> first image -> None."""
    images = list(project.images.all())
    purpose_image = next((img for img in images if img.purpose == purpose), None)
    if purpose_image:
        return purpose_image
    main_image = next((img for img in images if img.is_main), None)
    if main_image:
        return main_image
    return images[0] if images else None


def to_discover_item(project: Project) -> DiscoverProjectItem:
    icon = resolve_image_by_purpose(project, "icon")
    hero = resolve_image_by_purpose(project, "hero_banner")
    in_use = resolve_image_by_purpose(project, "in_use")

    return DiscoverProjectItem(
        project=project,
        icon_url=icon.url if icon else None,
        hero_banner_url=hero.url if hero else None,
        in_use_image_url=in_use.url if in_use else None,
        category_name=project.category.name if project.category else None,
        category_slug=project.category.slug if project.category else None,
        discussion_count=getattr(project, "discussion_count", 0) or 0,
    )


def to_list_item(project: Project) -> ProjectListItem:
    images = list(project.images.all())
    main_image = next((img for img in images if img.is_main), None)
    if not main_image and images:
        main_image = images[0]

    thumb_url = None
    variants = []
    if main_image:
        all_variants = list(main_image.variants.all())
        thumb = next((v for v in all_variants if v.size == "thumb"), None)
        if thumb:
            thumb_url = thumb.url
        variants = all_variants

    return ProjectListItem(
        project=project,
        main_image_url=main_image.url if main_image else None,
        main_image_thumb_url=thumb_url,
        main_image_variants=variants,
        tags=[t for t in project.tags.all() if t.status != "rejected"],
    )


class DjangoProjectQuery(ProjectQueryInterface):
    def get_by_id(self, project_id: UUID) -> Project:
        try:
            return _base_queryset().get(id=project_id)
        except Project.DoesNotExist:
            raise ProjectNotFoundError from None

    def get_for_owner(self, project_id: UUID, owner_id: UUID) -> Project:
        try:
            return _base_queryset().get(id=project_id, owner_id=owner_id)
        except Project.DoesNotExist:
            raise ProjectNotFoundError from None

    def list_approved(
        self,
        *,
        tags: list[str] | None = None,
        tech_stack: list[str] | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedProjects:
        if sort_by not in ALLOWED_SORT_FIELDS:
            allowed = ", ".join(sorted(ALLOWED_SORT_FIELDS))
            msg = f"Invalid sort field: {sort_by}. Allowed: {allowed}"
            raise ValueError(msg)

        queryset = _base_queryset().filter(status=ProjectStatus.APPROVED)

        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()

        if tech_stack:
            for tech in tech_stack:
                queryset = queryset.filter(tech_stack__icontains=tech)

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search),
            )

        order_field = f"-{sort_by}" if sort_order == "desc" else sort_by
        queryset = queryset.order_by(order_field)

        total = queryset.count()
        pages = ceil(total / per_page)
        offset = (page - 1) * per_page
        projects = queryset[offset : offset + per_page]

        return PaginatedProjects(
            projects=[to_list_item(p) for p in projects],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
        )

    def list_for_owner(self, owner_id: UUID) -> QuerySet[Project]:
        return _base_queryset().filter(owner_id=owner_id)

    def count_pending(self) -> int:
        return Project.objects.filter(status=ProjectStatus.PENDING).count()

    def get_project_with_owner(self, project_id: UUID) -> dict[str, Any]:
        try:
            project = Project.objects.select_related("owner").get(id=project_id)
        except Project.DoesNotExist:
            raise ProjectNotFoundError from None
        return {
            "id": project.id,
            "title": project.title,
            "owner_email": project.owner.email,
            "owner_first_name": project.owner.first_name,
        }

    def list_featured(self) -> list[DiscoverProjectItem]:
        projects = (
            _discover_queryset()
            .filter(status=ProjectStatus.APPROVED, is_featured=True)
            .order_by("-updated_at")
        )
        return [to_discover_item(p) for p in projects]

    def list_new_arrivals(
        self, *, min_count: int = 5, days: int = 30
    ) -> list[DiscoverProjectItem]:
        cutoff = timezone.now() - timedelta(days=days)
        arrival_date = Coalesce("approved_at", "created_at")
        recent = (
            _discover_queryset()
            .filter(status=ProjectStatus.APPROVED)
            .annotate(arrival_date=arrival_date)
            .filter(arrival_date__gte=cutoff)
            .order_by("-arrival_date")
        )
        if recent.count() < min_count:
            recent = (
                _discover_queryset()
                .filter(status=ProjectStatus.APPROVED)
                .annotate(arrival_date=arrival_date)
                .order_by("-arrival_date")[:min_count]
            )
        return [to_discover_item(p) for p in recent]

    def list_winners(self) -> list[WinnerItem]:
        competitions = (
            Competition.objects.filter(winner__isnull=False)
            .select_related("winner", "winner__category")
            .prefetch_related(
                "winner__won_competitions",
                Prefetch(
                    "winner__images",
                    queryset=ProjectImage.objects.filter(
                        upload_status="uploaded"
                    ),
                ),
            )
            .order_by("-end_date")
        )
        results = []
        for comp in competitions:
            project = comp.winner
            icon = resolve_image_by_purpose(project, "icon")
            hero = resolve_image_by_purpose(project, "hero_banner")
            in_use = resolve_image_by_purpose(project, "in_use")
            results.append(
                WinnerItem(
                    project=project,
                    icon_url=icon.url if icon else None,
                    hero_banner_url=hero.url if hero else None,
                    in_use_image_url=in_use.url if in_use else None,
                    competition_name=comp.name,
                    competition_slug=comp.slug,
                    competition_end_date=comp.end_date,
                )
            )
        return results

    def list_most_discussed(self) -> list[DiscoverProjectItem]:
        projects = (
            _discover_queryset()
            .filter(status=ProjectStatus.APPROVED)
            .annotate(discussion_count=_top_level_discussion_count())
            .filter(discussion_count__gt=0)
            .order_by("-discussion_count")
        )
        return [to_discover_item(p) for p in projects]

    def list_by_category(
        self, slug: str, sort: str = "newest"
    ) -> list[DiscoverProjectItem]:
        try:
            category = ProjectCategory.objects.get(slug=slug)
        except ProjectCategory.DoesNotExist:
            raise ProjectNotFoundError from None

        queryset = _discover_queryset().filter(
            status=ProjectStatus.APPROVED, category=category
        )

        if sort == "name":
            queryset = queryset.order_by("title")
        elif sort == "most-discussed":
            queryset = queryset.annotate(
                discussion_count=_top_level_discussion_count()
            ).order_by("-discussion_count")
        else:
            queryset = queryset.order_by("-approved_at")

        return [to_discover_item(p) for p in queryset]

    def list_categories(self) -> list[CategoryItem]:
        categories = (
            ProjectCategory.objects.annotate(
                project_count=Count(
                    "projects",
                    filter=Q(projects__status=ProjectStatus.APPROVED),
                )
            )
            .order_by("display_order", "name")
            .all()
        )
        return [
            CategoryItem(
                id=c.id,
                name=c.name,
                slug=c.slug,
                project_count=c.project_count,
            )
            for c in categories
        ]
