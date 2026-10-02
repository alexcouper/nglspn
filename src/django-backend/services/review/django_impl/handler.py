from collections.abc import Sequence
from uuid import UUID

from django.db import transaction

from apps.projects.models import (
    CompetitionReviewer,
    Project,
    ProjectRanking,
    ReviewStatus,
)
from services.review.django_impl.query import reviewable_competitions
from services.review.eligibility import EXCLUDED_PROJECT_STATUSES
from services.review.exceptions import (
    DuplicateProjectError,
    ProjectNotInCompetitionError,
    ReviewClosedError,
    ReviewerNotAssignedError,
)
from services.review.handler_interface import ReviewHandlerInterface


def _require_access(user_id: UUID, competition_id: UUID) -> None:
    """Raise unless the user may write to the competition's review now.

    A user who has a review but lost access (the competition left voting, or
    they left its group) is told the review is closed; anyone else is told
    they are not a reviewer.
    """
    if reviewable_competitions(user_id).filter(pk=competition_id).exists():
        return
    if CompetitionReviewer.objects.filter(
        user_id=user_id, competition_id=competition_id
    ).exists():
        raise ReviewClosedError
    raise ReviewerNotAssignedError


class DjangoReviewHandler(ReviewHandlerInterface):
    def replace_ballot(
        self,
        user_id: UUID,
        competition_id: UUID,
        project_ids: Sequence[UUID],
    ) -> None:
        _require_access(user_id, competition_id)

        if len(set(project_ids)) != len(project_ids):
            raise DuplicateProjectError

        eligible_ids = set(
            Project.objects.filter(competitions__id=competition_id)
            .exclude(status__in=EXCLUDED_PROJECT_STATUSES)
            .values_list("id", flat=True)
        )
        if not set(project_ids) <= eligible_ids:
            raise ProjectNotInCompetitionError

        with transaction.atomic():
            # The first save of a ballot is what makes it a review. Raising
            # below rolls a just-created row back with everything else.
            review, _ = CompetitionReviewer.objects.get_or_create(
                user_id=user_id, competition_id=competition_id
            )
            if review.status == ReviewStatus.COMPLETED:
                raise ReviewClosedError

            ProjectRanking.objects.filter(
                reviewer_id=user_id,
                competition_id=competition_id,
            ).delete()
            ProjectRanking.objects.bulk_create(
                [
                    ProjectRanking(
                        reviewer_id=user_id,
                        competition_id=competition_id,
                        project_id=project_id,
                        position=position,
                    )
                    for position, project_id in enumerate(project_ids, start=1)
                ]
            )

    def set_review_status(
        self,
        user_id: UUID,
        competition_id: UUID,
        status: ReviewStatus,
    ) -> None:
        _require_access(user_id, competition_id)
        CompetitionReviewer.objects.update_or_create(
            user_id=user_id,
            competition_id=competition_id,
            defaults={"status": status},
        )
