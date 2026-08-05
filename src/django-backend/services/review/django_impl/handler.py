from collections.abc import Sequence
from uuid import UUID

from django.db import transaction

from apps.projects.models import (
    CompetitionReviewer,
    Project,
    ProjectRanking,
    ReviewStatus,
)
from services.review.django_impl.query import EXCLUDED_PROJECT_STATUSES
from services.review.exceptions import (
    DuplicateProjectError,
    ProjectNotInCompetitionError,
    ReviewClosedError,
    ReviewerNotAssignedError,
)
from services.review.handler_interface import ReviewHandlerInterface

CLOSED_REVIEW_STATUSES = (ReviewStatus.COMPLETED, ReviewStatus.ENDED)


class DjangoReviewHandler(ReviewHandlerInterface):
    def end_review_period(self, competition_id: UUID) -> int:
        return CompetitionReviewer.objects.filter(
            competition_id=competition_id,
            status=ReviewStatus.IN_PROGRESS,
        ).update(status=ReviewStatus.ENDED)

    def replace_ballot(
        self,
        user_id: UUID,
        competition_id: UUID,
        project_ids: Sequence[UUID],
    ) -> None:
        assignment = CompetitionReviewer.objects.filter(
            user_id=user_id,
            competition_id=competition_id,
        ).first()
        if assignment is None:
            raise ReviewerNotAssignedError
        if assignment.status in CLOSED_REVIEW_STATUSES:
            raise ReviewClosedError

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
