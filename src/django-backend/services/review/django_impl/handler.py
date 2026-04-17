from uuid import UUID

from apps.projects.models import CompetitionReviewer, ReviewStatus
from services.review.handler_interface import ReviewHandlerInterface


class DjangoReviewHandler(ReviewHandlerInterface):
    def end_review_period(self, competition_id: UUID) -> int:
        return CompetitionReviewer.objects.filter(
            competition_id=competition_id,
            status=ReviewStatus.IN_PROGRESS,
        ).update(status=ReviewStatus.ENDED)
