import uuid

from django.db.models import Count
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router

from api.schemas.competition import (
    CompetitionHighlightsResponse,
    CompetitionListResponse,
    CompetitionOverviewListResponse,
    CompetitionOverviewResponse,
    CompetitionResponse,
    CompetitionSummaryResponse,
)
from api.schemas.errors import Error
from apps.projects.models import Competition, CompetitionStatus, Project, ProjectStatus
from services import REPO


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
            "projects__tags",
            # `to_list_item(competition.winner)` reads the relation as-is and
            # falls back to `images[0]`, so an unfiltered prefetch lets an
            # article figure or a PUT that never landed become the winner's
            # card image.
            REPO.images.gallery_prefetch("winner__images"),
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
    "/highlights",
    response={200: CompetitionHighlightsResponse},
    tags=["Competitions"],
)
def get_highlights(request: HttpRequest) -> CompetitionHighlightsResponse:
    base_qs = Competition.objects.annotate(project_count=Count("projects"))

    active = list(
        base_qs.filter(
            status__in=[
                CompetitionStatus.ACCEPTING_APPLICATIONS,
                CompetitionStatus.VOTING,
            ]
        ).order_by("-start_date")
    )
    recent = (
        base_qs.filter(status=CompetitionStatus.CLOSED)
        .order_by("-voting_end_date", "-submission_deadline")
        .first()
    )

    competitions = [CompetitionSummaryResponse.from_competition(c) for c in active]
    if recent:
        competitions.append(CompetitionSummaryResponse.from_competition(recent))

    return CompetitionHighlightsResponse(competitions=competitions)


@router.get(
    "/{competition_id}",
    response={200: CompetitionResponse, 404: Error},
    tags=["Competitions"],
)
def get_competition(request: HttpRequest, competition_id: str) -> CompetitionResponse:
    queryset = Competition.objects.select_related("winner").prefetch_related(
        "projects",
        "projects__tags",
        # See `list_competitions_with_projects`: the winner's gallery has to be
        # filtered before `to_list_item` picks from it.
        REPO.images.gallery_prefetch("winner__images"),
        "winner__tags",
    )
    if is_valid_uuid(competition_id):
        competition = get_object_or_404(queryset, id=competition_id)
    else:
        competition = get_object_or_404(queryset, slug=competition_id)
    return CompetitionResponse.from_competition(competition)
