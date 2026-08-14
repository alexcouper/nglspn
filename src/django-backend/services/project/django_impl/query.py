from datetime import timedelta
from math import ceil
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from django.db.models import Count, Q, QuerySet, prefetch_related_objects
from django.db.models.functions import Coalesce, Lower
from django.utils import timezone

from apps.projects.models import (
    Competition,
    CompetitionEntry,
    CompetitionStatus,
    ContributorRole,
    Project,
    ProjectCategory,
    ProjectContributor,
    ProjectImage,
    ProjectStatus,
)
from services.images.django_impl.query import gallery_prefetch
from services.project.exceptions import ProjectNotFoundError
from services.project.query_interface import (
    CategoryItem,
    CompetitionOpportunity,
    CompetitionStanding,
    DiscoverProjectItem,
    IneligibleReason,
    PaginatedProjects,
    ProjectEntry,
    ProjectListItem,
    ProjectQueryInterface,
    WinnerItem,
)

ALLOWED_SORT_FIELDS = {"created_at", "title", "updated_at"}


def _top_level_discussion_count() -> Count:
    return Count("discussions", filter=Q(discussions__parent__isnull=True))


def _discover_queryset() -> QuerySet[Project]:
    return Project.objects.select_related("creator", "category").prefetch_related(
        "won_competitions",
        gallery_prefetch(),
    )


def _base_queryset() -> QuerySet[Project]:
    return Project.objects.select_related("creator").prefetch_related(
        "tags",
        "tags__category",
        "won_competitions",
        "contributors__user",
        gallery_prefetch(),
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
    """Fallback chain: role-specific image -> main image -> first image -> None."""
    images = list(project.images.all())

    role_map = {
        "icon": "is_icon",
        "hero_banner": "is_hero",
        "in_use": "is_usage",
    }
    role_field = role_map.get(purpose)
    role_image = (
        next((img for img in images if getattr(img, role_field, False)), None)
        if role_field
        else None
    )

    if role_image:
        return role_image
    main_image = next((img for img in images if img.is_main), None)
    if main_image:
        return main_image
    return images[0] if images else None


def variant_url(image: "ProjectImage | None", size: str) -> str | None:
    if image is None:
        return None
    variants = list(image.variants.all())
    variant = next((v for v in variants if v.size == size), None)
    return variant.url if variant else image.url


def to_discover_item(project: Project) -> DiscoverProjectItem:
    icon = resolve_image_by_purpose(project, "icon")
    hero = resolve_image_by_purpose(project, "hero_banner")
    in_use = resolve_image_by_purpose(project, "in_use")

    return DiscoverProjectItem(
        project=project,
        icon_url=variant_url(icon, "thumb"),
        hero_banner_url=variant_url(hero, "large"),
        in_use_image_url=variant_url(in_use, "medium"),
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

    def get_by_identifier(self, identifier: str) -> Project:
        try:
            uuid_value = UUID(identifier)
        except (ValueError, TypeError, AttributeError):
            uuid_value = None

        qs = _base_queryset()
        try:
            if uuid_value is not None:
                return qs.get(id=uuid_value)
            return qs.get(slug=identifier)
        except Project.DoesNotExist:
            raise ProjectNotFoundError from None

    def get_for_owner(self, project_id: UUID, owner_id: UUID) -> Project:
        try:
            project = _base_queryset().get(id=project_id)
        except Project.DoesNotExist:
            raise ProjectNotFoundError from None
        if not self.user_can_edit(project.id, owner_id):
            raise ProjectNotFoundError
        return project

    def user_can_edit(self, project_id: UUID | None, user_id: UUID | None) -> bool:
        if project_id is None or user_id is None:
            return False
        return ProjectContributor.objects.filter(
            project_id=project_id,
            user_id=user_id,
            full_edit=True,
        ).exists()

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
        # Creator-scoped, but tip-off projects belong in /tip-offs: for tip-offs
        # the tipster is the creator, so without this exclusion they would
        # appear in both /my-projects and /my-projects/tip-offs.
        return _base_queryset().filter(creator_id=owner_id, is_community_tipoff=False)

    def list_tip_offs_for(self, user_id: UUID) -> QuerySet[Project]:
        return (
            _base_queryset()
            .filter(
                contributors__user_id=user_id,
                contributors__role=ContributorRole.TIPSTER,
                contributors__full_edit=True,
            )
            .distinct()
        )

    def list_notifiable_contributors(
        self, project_id: UUID
    ) -> QuerySet[ProjectContributor]:
        return (
            ProjectContributor.objects.filter(
                project_id=project_id,
                full_edit=True,
            )
            .exclude(user__is_system_user=True)
            .select_related("user")
        )

    def count_pending(self) -> int:
        return Project.objects.filter(status=ProjectStatus.PENDING).count()

    def get_project_with_owner(self, project_id: UUID) -> dict[str, Any]:
        try:
            project = Project.objects.select_related("creator").get(id=project_id)
        except Project.DoesNotExist:
            raise ProjectNotFoundError from None
        return {
            "id": project.id,
            "title": project.title,
            "owner_email": project.creator.email,
            "owner_first_name": project.creator.first_name,
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
        base = _discover_queryset().filter(
            status=ProjectStatus.APPROVED, is_community_tipoff=False
        )
        recent = (
            base.annotate(arrival_date=arrival_date)
            .filter(arrival_date__gte=cutoff)
            .order_by("-arrival_date")
        )
        if recent.count() < min_count:
            recent = base.annotate(arrival_date=arrival_date).order_by("-arrival_date")[
                :min_count
            ]
        return [to_discover_item(p) for p in recent]

    def list_recent_tipoffs(
        self, *, min_count: int = 5, days: int = 30
    ) -> list[DiscoverProjectItem]:
        cutoff = timezone.now() - timedelta(days=days)
        arrival_date = Coalesce("approved_at", "created_at")
        base = _discover_queryset().filter(
            status=ProjectStatus.APPROVED, is_community_tipoff=True
        )
        recent = (
            base.annotate(arrival_date=arrival_date)
            .filter(arrival_date__gte=cutoff)
            .order_by("-arrival_date")
        )
        if recent.count() < min_count:
            recent = base.annotate(arrival_date=arrival_date).order_by("-arrival_date")[
                :min_count
            ]
        return [to_discover_item(p) for p in recent]

    def list_winners(self) -> list[WinnerItem]:
        competitions = (
            Competition.objects.filter(winner__isnull=False)
            .select_related("winner", "winner__category")
            .prefetch_related(
                "winner__won_competitions",
                gallery_prefetch("winner__images"),
            )
            .order_by("-submission_deadline")
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
                    icon_url=variant_url(icon, "thumb"),
                    hero_banner_url=variant_url(hero, "large"),
                    in_use_image_url=variant_url(in_use, "medium"),
                    competition_name=comp.name,
                    competition_slug=comp.slug,
                    competition_submission_deadline=comp.submission_deadline,
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
            queryset = queryset.order_by(Lower("title"))
        elif sort == "most-discussed":
            queryset = queryset.annotate(
                discussion_count=_top_level_discussion_count()
            ).order_by("-discussion_count")
        else:
            arrival_date = Coalesce("approved_at", "created_at")
            queryset = queryset.annotate(arrival_date=arrival_date).order_by(
                "-arrival_date"
            )

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

    def get_project_icon_url(self, project: Project | UUID) -> str | None:
        if isinstance(project, UUID):
            try:
                project = Project.objects.get(id=project)
            except Project.DoesNotExist:
                return None
        icon = resolve_image_by_purpose(project, "icon")
        return variant_url(icon, "thumb")

    def competition_standing(self, project: Project) -> CompetitionStanding:
        return _standing(project, _entries_for(project), _open_competitions())

    def with_competition_standing(
        self, projects: QuerySet[Project] | list[Project]
    ) -> list[Project]:
        """Stamp each project's standing, at a fixed cost for the whole list.

        The open competitions are resolved once rather than per project, and
        the entries come from a prefetch, so a list of fifty projects costs the
        same two extra queries as a list of one.
        """
        projects = list(projects)
        # Prefetched either way, so `.all()` below reads the cache rather than
        # issuing a query per project.
        prefetch_related_objects(projects, "competition_entries__competition")

        open_competitions = _open_competitions()
        for project in projects:
            project._competition_standing = _standing(  # noqa: SLF001
                project,
                list(project.competition_entries.all()),
                open_competitions,
            )
        return projects


def _open_competitions() -> list[Competition]:
    return list(
        Competition.objects.filter(
            status=CompetitionStatus.ACCEPTING_APPLICATIONS
        ).order_by("-start_date")
    )


def _entries_for(project: Project) -> list[CompetitionEntry]:
    return list(project.competition_entries.select_related("competition"))


def _standing(
    project: Project,
    entries: list[CompetitionEntry],
    open_competitions: list[Competition],
) -> CompetitionStanding:
    newest_first = sorted(entries, key=lambda entry: entry.entered_at, reverse=True)

    # One blocker per series, the most recent, so a project that somehow holds
    # two entries in a series is told about the one it will recognise.
    blocking_by_series: dict[str, Competition] = {}
    for entry in newest_first:
        blocking_by_series.setdefault(entry.competition.entry_series, entry.competition)

    return CompetitionStanding(
        entries=[
            ProjectEntry(
                competition=entry.competition,
                entered_at=entry.entered_at,
                entered_via=entry.entered_via,
            )
            for entry in newest_first
        ],
        opportunities=[
            _opportunity(project, competition, blocking_by_series)
            for competition in open_competitions
        ],
    )


def _opportunity(
    project: Project,
    competition: Competition,
    blocking_by_series: dict[str, Competition],
) -> CompetitionOpportunity:
    """The four ordered rules, first match wins."""
    if project.is_community_tipoff:
        reason, blocking = IneligibleReason.COMMUNITY_PROJECT, None
    elif project.status in (ProjectStatus.REJECTED, ProjectStatus.ICE_BOX):
        reason, blocking = IneligibleReason.PROJECT_STATUS, None
    elif competition.entry_series in blocking_by_series:
        reason = IneligibleReason.ALREADY_IN_SERIES
        blocking = blocking_by_series[competition.entry_series]
    else:
        reason, blocking = None, None

    return CompetitionOpportunity(
        competition=competition,
        eligible=reason is None,
        reason=reason,
        blocking_entry=blocking,
    )
