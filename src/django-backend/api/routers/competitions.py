from typing import Any

from django.http import HttpRequest
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
from services import REPO
from services.competitions.exceptions import CompetitionNotFoundError
from services.project.django_impl import to_list_item


def _projects(competition: Any) -> list:
    return list(competition.projects.all())


def _count_pending(projects: list) -> int:
    return sum(1 for p in projects if p.status == "pending")


def _approved_project_items(projects: list) -> list:
    approved = [p for p in projects if p.status == "approved"]
    approved.sort(key=lambda p: p.title.lower())
    return [to_list_item(p) for p in approved]


router = Router()


@router.get("", response={200: CompetitionOverviewListResponse}, tags=["Competitions"])
def list_competitions(request: HttpRequest) -> CompetitionOverviewListResponse:
    competitions = REPO.competitions.list_all()
    pending_count = REPO.competitions.count_pending_projects()
    overviews = []
    for c in competitions:
        projects = _projects(c)
        overviews.append(
            CompetitionOverviewResponse.from_competition(
                c,
                project_count=len(projects),
                pending_projects_count=_count_pending(projects),
            )
        )
    return CompetitionOverviewListResponse(
        competitions=overviews,
        pending_projects_count=pending_count,
    )


@router.get(
    "/with-projects", response={200: CompetitionListResponse}, tags=["Competitions"]
)
def list_competitions_with_projects(request: HttpRequest) -> CompetitionListResponse:
    competitions = REPO.competitions.list_with_projects()
    pending_count = REPO.competitions.count_pending_projects()
    items = []
    for c in competitions:
        projects = _projects(c)
        items.append(
            CompetitionResponse.from_competition(
                c,
                approved_project_items=_approved_project_items(projects),
                winner_item=to_list_item(c.winner) if c.winner else None,
                project_count=len(projects),
                pending_projects_count=_count_pending(projects),
            )
        )
    return CompetitionListResponse(
        competitions=items,
        pending_projects_count=pending_count,
    )


@router.get(
    "/highlights",
    response={200: CompetitionHighlightsResponse},
    tags=["Competitions"],
)
def get_highlights(request: HttpRequest) -> CompetitionHighlightsResponse:
    highlights = REPO.competitions.list_highlights()
    return CompetitionHighlightsResponse(
        competitions=[CompetitionSummaryResponse.from_highlight(h) for h in highlights]
    )


@router.get(
    "/{competition_id}",
    response={200: CompetitionResponse, 404: Error},
    tags=["Competitions"],
)
def get_competition(
    request: HttpRequest, competition_id: str
) -> CompetitionResponse | tuple[int, dict[str, str]]:
    try:
        competition = REPO.competitions.get_by_id_or_slug(competition_id)
    except CompetitionNotFoundError:
        return 404, {"detail": "Not Found"}
    projects = _projects(competition)
    return CompetitionResponse.from_competition(
        competition,
        approved_project_items=_approved_project_items(projects),
        winner_item=to_list_item(competition.winner) if competition.winner else None,
        project_count=len(projects),
        pending_projects_count=_count_pending(projects),
    )
