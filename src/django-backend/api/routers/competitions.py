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

router = Router()


@router.get("", response={200: CompetitionOverviewListResponse}, tags=["Competitions"])
def list_competitions(request: HttpRequest) -> CompetitionOverviewListResponse:
    items = REPO.competitions.list_all()
    pending_count = REPO.competitions.count_pending_projects()
    return CompetitionOverviewListResponse(
        competitions=[
            CompetitionOverviewResponse.from_competition(
                item.competition,
                project_count=item.project_count,
                pending_projects_count=item.pending_projects_count,
            )
            for item in items
        ],
        pending_projects_count=pending_count,
    )


@router.get(
    "/with-projects", response={200: CompetitionListResponse}, tags=["Competitions"]
)
def list_competitions_with_projects(request: HttpRequest) -> CompetitionListResponse:
    items = REPO.competitions.list_with_projects()
    pending_count = REPO.competitions.count_pending_projects()
    return CompetitionListResponse(
        competitions=[
            CompetitionResponse.from_competition(
                item.competition,
                project_items=item.project_items,
                winner_item=item.winner_item,
                project_count=item.project_count,
                pending_projects_count=item.pending_projects_count,
            )
            for item in items
        ],
        pending_projects_count=pending_count,
    )


@router.get(
    "/highlights",
    response={200: CompetitionHighlightsResponse},
    tags=["Competitions"],
)
def get_highlights(request: HttpRequest) -> CompetitionHighlightsResponse:
    highlights = REPO.competitions.list_highlights()
    competitions = [
        CompetitionSummaryResponse.from_highlight_item(h) for h in highlights
    ]
    return CompetitionHighlightsResponse(competitions=competitions)


@router.get(
    "/{competition_id}",
    response={200: CompetitionResponse, 404: Error},
    tags=["Competitions"],
)
def get_competition(
    request: HttpRequest, competition_id: str
) -> CompetitionResponse | tuple[int, Error]:
    try:
        item = REPO.competitions.get_by_id_or_slug(competition_id)
    except CompetitionNotFoundError:
        return 404, Error(detail="Competition not found")
    return CompetitionResponse.from_competition(
        item.competition,
        project_items=item.project_items,
        winner_item=item.winner_item,
        project_count=item.project_count,
        pending_projects_count=item.pending_projects_count,
    )
