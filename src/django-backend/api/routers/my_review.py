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
from apps.projects.models import (
    Competition,
    CompetitionReviewer,
    Project,
    ProjectRanking,
    ProjectStatus,
    ReviewStatus,
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
    """List all competitions the current user is assigned to review."""
    assignments = CompetitionReviewer.objects.filter(user=request.auth).select_related(
        "competition"
    )

    competitions = [
        ReviewCompetitionResponse(
            id=a.competition.id,
            name=a.competition.name,
            start_date=a.competition.start_date,
            end_date=a.competition.end_date,
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
    """Get competition details with projects and reviewer's rankings."""
    assignment = CompetitionReviewer.objects.filter(
        user=request.auth,
        competition_id=competition_id,
    ).first()

    if not assignment:
        return 404, Error(detail="Competition not found")

    competition = Competition.objects.prefetch_related(
        "projects",
        "projects__images",
    ).get(id=competition_id)

    rankings = {
        r.project_id: r.position
        for r in ProjectRanking.objects.filter(
            reviewer=request.auth,
            competition=competition,
        )
    }

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
        end_date=competition.end_date,
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
    """Update rankings for projects in a competition."""
    assignment = CompetitionReviewer.objects.filter(
        user=request.auth,
        competition_id=competition_id,
    ).first()

    if not assignment:
        return 404, Error(detail="Competition not found")

    if assignment.status == ReviewStatus.COMPLETED:
        return 400, Error(detail="Cannot update rankings for a completed review")

    competition_project_ids = set(
        Competition.objects.filter(id=competition_id)
        .exclude(projects__status__in=EXCLUDED_PROJECT_STATUSES)
        .values_list("projects__id", flat=True)
    )
    submitted_project_ids = set(payload.project_ids)

    invalid_ids = submitted_project_ids - competition_project_ids
    if invalid_ids:
        return 400, Error(
            detail="One or more projects do not belong to this competition"
        )

    # Delete existing rankings and create new ones
    ProjectRanking.objects.filter(
        reviewer=request.auth,
        competition_id=competition_id,
    ).delete()

    ProjectRanking.objects.bulk_create(
        [
            ProjectRanking(
                reviewer=request.auth,
                competition_id=competition_id,
                project_id=project_id,
                position=position,
            )
            for position, project_id in enumerate(payload.project_ids, start=1)
        ]
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
    """Update the reviewer's status for a competition."""
    updated = CompetitionReviewer.objects.filter(
        user=request.auth,
        competition_id=competition_id,
    ).update(status=payload.status.value)

    if not updated:
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
    """Get project details for a reviewer.

    Returns the project if the user is assigned as a reviewer to any
    competition that contains this project. Returns 404 otherwise.
    """
    # Check if user is a reviewer for any competition containing this project
    # and that the project is not rejected or in ice box
    has_access = CompetitionReviewer.objects.filter(
        user=request.auth,
        competition__projects__id=project_id,
    ).exists()

    if not has_access:
        return 404, Error(detail="Project not found")

    try:
        project = (
            Project.objects.select_related("owner")
            .prefetch_related("tags", "tags__category", "images")
            .exclude(status__in=EXCLUDED_PROJECT_STATUSES)
            .get(id=project_id)
        )
    except Project.DoesNotExist:
        return 404, Error(detail="Project not found")

    return project
