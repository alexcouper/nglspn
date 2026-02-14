import uuid

from django.db.models import Count
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router

from api.schemas.competition import (
    ActiveOrRecentResponse,
    CompetitionListResponse,
    CompetitionOverviewListResponse,
    CompetitionOverviewResponse,
    CompetitionResponse,
    CompetitionSummaryResponse,
)
from api.schemas.errors import Error
from apps.projects.models import Competition, CompetitionStatus, Project, ProjectStatus


def is_valid_uuid(value: str) -> bool:
    """Check if string is a valid UUID."""
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    else:
        return True


router = Router()


@router.get("", response={200: CompetitionOverviewListResponse}, tags=["Competitions"])
def list_competitions(request: HttpRequest) -> CompetitionOverviewListResponse:
    competitions = Competition.objects.prefetch_related("projects").all()
    pending_count = Project.objects.filter(status=ProjectStatus.PENDING).count()
    return CompetitionOverviewListResponse(
        competitions=[
            CompetitionOverviewResponse.from_competition(c) for c in competitions
        ],
        pending_projects_count=pending_count,
    )


@router.get(
    "/with-projects", response={200: CompetitionListResponse}, tags=["Competitions"]
)
def list_competitions_with_projects(request: HttpRequest) -> CompetitionListResponse:
    competitions = (
        Competition.objects.select_related("winner")
        .prefetch_related(
            "projects",
            "projects__images",
            "projects__tags",
            "winner__images",
            "winner__tags",
        )
        .all()
    )
    pending_count = Project.objects.filter(status=ProjectStatus.PENDING).count()
    return CompetitionListResponse(
        competitions=[CompetitionResponse.from_competition(c) for c in competitions],
        pending_projects_count=pending_count,
    )


@router.get(
    "/active-or-most-recent",
    response={200: ActiveOrRecentResponse},
    tags=["Competitions"],
)
def get_active_or_most_recent(request: HttpRequest) -> ActiveOrRecentResponse:
    base_qs = Competition.objects.annotate(project_count=Count("projects"))

    active = base_qs.filter(status=CompetitionStatus.ACCEPTING_APPLICATIONS).first()
    recent = (
        base_qs.filter(status=CompetitionStatus.CLOSED).order_by("-end_date").first()
    )

    return ActiveOrRecentResponse(
        active=CompetitionSummaryResponse.from_competition(active) if active else None,
        recent=CompetitionSummaryResponse.from_competition(recent) if recent else None,
    )


@router.get(
    "/{competition_id}",
    response={200: CompetitionResponse, 404: Error},
    tags=["Competitions"],
)
def get_competition(request: HttpRequest, competition_id: str) -> CompetitionResponse:
    queryset = Competition.objects.select_related("winner").prefetch_related(
        "projects",
        "projects__images",
        "projects__tags",
        "winner__images",
        "winner__tags",
    )
    if is_valid_uuid(competition_id):
        competition = get_object_or_404(queryset, id=competition_id)
    else:
        competition = get_object_or_404(queryset, slug=competition_id)
    return CompetitionResponse.from_competition(competition)
