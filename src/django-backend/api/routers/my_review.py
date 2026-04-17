from django.http import HttpRequest
from ninja import Router

from api.auth.security import auth
from api.schemas.errors import Error
from api.schemas.my_review import (
    RankingUpdateRequest,
    ReviewCompetitionDetailResponse,
    ReviewCompetitionListResponse,
    ReviewCompetitionResponse,
    ReviewProjectDetailResponse,
    ReviewProjectResponse,
    StatusUpdateRequest,
    SuccessResponse,
)
from apps.projects.models import Project, ProjectStatus
from services import HANDLERS, REPO
from services.review.exceptions import (
    InvalidProjectIdsError,
    ReviewAlreadyCompletedError,
    ReviewNotFoundError,
)

router = Router()

EXCLUDED_PROJECT_STATUSES = [ProjectStatus.REJECTED, ProjectStatus.ICE_BOX]


@router.get(
    "/competitions",
    response={200: ReviewCompetitionListResponse},
    auth=auth,
    tags=["My Review"],
)
def list_my_review_competitions(request: HttpRequest) -> ReviewCompetitionListResponse:
    assignments = REPO.review.list_reviewer_assignments(request.auth.id)

    competitions = [
        ReviewCompetitionResponse(
            id=a.competition.id,
            name=a.competition.name,
            start_date=a.competition.start_date,
            submission_deadline=a.competition.submission_deadline,
            image_url=a.competition.image_url,
            project_count=a.competition.projects.exclude(
                status__in=EXCLUDED_PROJECT_STATUSES
            ).count(),
            my_review_status=a.status,
        )
        for a in assignments
    ]
    return ReviewCompetitionListResponse(competitions=competitions)


@router.get(
    "/competitions/{competition_id}",
    response={200: ReviewCompetitionDetailResponse, 404: Error},
    auth=auth,
    tags=["My Review"],
)
def get_my_review_competition(
    request: HttpRequest,
    competition_id: str,
) -> ReviewCompetitionDetailResponse | tuple[int, Error]:
    assignment = REPO.review.get_reviewer_assignment(request.auth.id, competition_id)

    if not assignment:
        return 404, Error(detail="Competition not found")

    competition = REPO.review.get_competition_with_projects(competition_id)
    rankings = REPO.review.get_reviewer_rankings(request.auth.id, competition_id)

    projects = [
        ReviewProjectResponse(
            id=p.id,
            title=p.title,
            description=p.description,
            website_url=p.website_url,
            main_image_url=ReviewProjectResponse.resolve_main_image_url(p),
            my_ranking=rankings.get(p.id),
        )
        for p in competition.projects.exclude(status__in=EXCLUDED_PROJECT_STATUSES)
    ]

    return ReviewCompetitionDetailResponse(
        id=competition.id,
        name=competition.name,
        start_date=competition.start_date,
        submission_deadline=competition.submission_deadline,
        my_review_status=assignment.status,
        projects=projects,
    )


@router.put(
    "/competitions/{competition_id}/rankings",
    response={200: SuccessResponse, 400: Error, 404: Error},
    auth=auth,
    tags=["My Review"],
)
def update_rankings(
    request: HttpRequest,
    competition_id: str,
    payload: RankingUpdateRequest,
) -> SuccessResponse | tuple[int, Error]:
    try:
        HANDLERS.review.update_rankings(
            user_id=request.auth.id,
            competition_id=competition_id,
            project_ids=payload.project_ids,
        )
    except ReviewNotFoundError:
        return 404, Error(detail="Competition not found")
    except ReviewAlreadyCompletedError:
        return 400, Error(detail="Cannot update rankings for a completed review")
    except InvalidProjectIdsError:
        return 400, Error(
            detail="One or more projects do not belong to this competition"
        )

    return SuccessResponse()


@router.put(
    "/competitions/{competition_id}/status",
    response={200: SuccessResponse, 404: Error},
    auth=auth,
    tags=["My Review"],
)
def update_review_status(
    request: HttpRequest,
    competition_id: str,
    payload: StatusUpdateRequest,
) -> SuccessResponse | tuple[int, Error]:
    try:
        HANDLERS.review.update_review_status(
            user_id=request.auth.id,
            competition_id=competition_id,
            status=payload.status.value,
        )
    except ReviewNotFoundError:
        return 404, Error(detail="Competition not found")

    return SuccessResponse()


@router.get(
    "/projects/{project_id}",
    response={200: ReviewProjectDetailResponse, 404: Error},
    auth=auth,
    tags=["My Review"],
)
def get_review_project(
    request: HttpRequest,
    project_id: str,
) -> Project | tuple[int, Error]:
    try:
        return REPO.review.get_review_project(request.auth.id, project_id)
    except ReviewNotFoundError:
        return 404, Error(detail="Project not found")
