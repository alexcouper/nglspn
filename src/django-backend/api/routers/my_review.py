from django.db.models import Prefetch
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
    ReviewStatusEnum,
    StatusUpdateRequest,
    SuccessResponse,
)
from apps.projects.models import (
    Competition,
    CompetitionReviewer,
    Project,
    ProjectImage,
)
from services import HANDLERS, REPO
from services.review.eligibility import EXCLUDED_PROJECT_STATUSES
from services.review.exceptions import (
    DuplicateProjectError,
    ProjectNotInCompetitionError,
    ReviewClosedError,
    ReviewerNotAssignedError,
)
from services.review.query_interface import ReviewProjectItem

router = Router()


def _project_response(
    item: ReviewProjectItem, position: int | None
) -> ReviewProjectResponse:
    """Map a ballot entry onto the response. The service resolved the images."""
    return ReviewProjectResponse(
        id=item.project.id,
        slug=item.project.slug,
        title=item.project.title,
        tagline=item.project.tagline,
        description=item.project.description,
        website_url=item.project.website_url,
        hero_banner_url=item.hero_banner_url,
        in_use_image_url=item.in_use_image_url,
        category_name=item.category_name,
        my_ranking=position,
    )


@router.get(
    "/competitions",
    response={200: ReviewCompetitionListResponse},
    auth=auth,
    tags=["My Review"],
)
def list_my_review_competitions(request: HttpRequest) -> ReviewCompetitionListResponse:
    """List all competitions the current user is assigned to review."""
    assignments = (
        CompetitionReviewer.objects.filter(user=request.auth)
        .select_related("competition")
        .order_by("-competition__start_date")
    )

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
    """Get competition details with projects and reviewer's rankings."""
    assignment = CompetitionReviewer.objects.filter(
        user=request.auth,
        competition_id=competition_id,
    ).first()

    if not assignment:
        return 404, Error(detail="Competition not found")

    competition = Competition.objects.get(id=competition_id)
    ballot = REPO.reviews.get_reviewer_projects(request.auth.id, competition.id)

    return ReviewCompetitionDetailResponse(
        id=competition.id,
        name=competition.name,
        start_date=competition.start_date,
        submission_deadline=competition.submission_deadline,
        my_review_status=assignment.status,
        ranked_projects=[
            _project_response(item, position)
            for position, item in enumerate(ballot.ranked, start=1)
        ],
        pool_projects=[_project_response(item, None) for item in ballot.pool],
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
    """Replace the reviewer's ballot for a competition.

    The payload is the ballot in full: projects left out are unranked, and an
    empty list is a valid abstention.
    """
    try:
        HANDLERS.reviews.replace_ballot(
            request.auth.id, competition_id, payload.project_ids
        )
    except ReviewerNotAssignedError:
        return 404, Error(detail="Competition not found")
    except ReviewClosedError:
        return 400, Error(detail="Cannot update rankings for a closed review")
    except DuplicateProjectError:
        return 400, Error(detail="The same project was ranked more than once")
    except ProjectNotInCompetitionError:
        return 400, Error(
            detail="One or more projects do not belong to this competition"
        )

    return SuccessResponse()


@router.put(
    "/competitions/{competition_id}/status",
    response={200: SuccessResponse, 400: Error, 404: Error},
    auth=auth,
    tags=["My Review"],
)
def update_review_status(
    request: HttpRequest,
    competition_id: str,
    payload: StatusUpdateRequest,
) -> SuccessResponse | tuple[int, Error]:
    """Update the reviewer's status for a competition."""
    if payload.status == ReviewStatusEnum.ENDED:
        return 400, Error(
            detail="Reviewers cannot set status to 'ended'; that is set by an admin."
        )

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
            Project.objects.select_related("creator")
            .prefetch_related(
                "tags",
                "tags__category",
                "contributors__user",
                Prefetch(
                    "images",
                    queryset=ProjectImage.objects.filter(
                        upload_status="uploaded"
                    ).prefetch_related("variants"),
                ),
                "won_competitions",
            )
            .exclude(status__in=EXCLUDED_PROJECT_STATUSES)
            .get(id=project_id)
        )
    except Project.DoesNotExist:
        return 404, Error(detail="Project not found")

    project.is_followed = REPO.follows.is_followed(request.auth.id, project)
    return project
