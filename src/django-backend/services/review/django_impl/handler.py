from uuid import UUID

from apps.projects.models import (
    CompetitionReviewer,
    ProjectRanking,
    ProjectStatus,
    ReviewStatus,
)
from services.review.exceptions import (
    InvalidProjectIdsError,
    ReviewAlreadyCompletedError,
    ReviewNotFoundError,
)
from services.review.handler_interface import ReviewHandlerInterface
from services.review.query_interface import ReviewQueryInterface


class DjangoReviewHandler(ReviewHandlerInterface):
    @property
    def _query(self) -> ReviewQueryInterface:
        from services import REPO  # noqa: PLC0415

        return REPO.review

    def update_rankings(
        self,
        *,
        user_id: UUID,
        competition_id: UUID,
        project_ids: list[UUID],
    ) -> None:
        assignment = self._query.get_reviewer_assignment(user_id, competition_id)
        if not assignment:
            raise ReviewNotFoundError

        if assignment.status == ReviewStatus.COMPLETED:
            raise ReviewAlreadyCompletedError

        excluded = [ProjectStatus.REJECTED, ProjectStatus.ICE_BOX]
        competition_project_ids = self._query.get_competition_project_ids(
            competition_id, excluded
        )
        submitted_project_ids = set(project_ids)
        invalid_ids = submitted_project_ids - competition_project_ids
        if invalid_ids:
            raise InvalidProjectIdsError

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

    def update_review_status(
        self,
        *,
        user_id: UUID,
        competition_id: UUID,
        status: str,
    ) -> None:
        updated = CompetitionReviewer.objects.filter(
            user_id=user_id,
            competition_id=competition_id,
        ).update(status=status)

        if not updated:
            raise ReviewNotFoundError
