from uuid import UUID

from django.db.models import Prefetch

from apps.projects.models import (
    Competition,
    CompetitionReviewer,
    Project,
    ProjectImage,
    ProjectRanking,
    ProjectStatus,
)
from services.review.exceptions import ReviewNotFoundError
from services.review.query_interface import ReviewQueryInterface

EXCLUDED_PROJECT_STATUSES = [ProjectStatus.REJECTED, ProjectStatus.ICE_BOX]


class DjangoReviewQuery(ReviewQueryInterface):
    def list_reviewer_assignments(self, user_id: UUID) -> list[CompetitionReviewer]:
        return list(
            CompetitionReviewer.objects.filter(user_id=user_id).select_related(
                "competition"
            )
        )

    def get_reviewer_assignment(
        self, user_id: UUID, competition_id: UUID
    ) -> CompetitionReviewer | None:
        return (
            CompetitionReviewer.objects.filter(
                user_id=user_id, competition_id=competition_id
            )
            .select_related("competition")
            .first()
        )

    def get_competition_with_projects(self, competition_id: UUID) -> Competition:
        try:
            return Competition.objects.prefetch_related(
                "projects",
                "projects__images",
            ).get(id=competition_id)
        except Competition.DoesNotExist:
            raise ReviewNotFoundError from None

    def get_reviewer_rankings(
        self, user_id: UUID, competition_id: UUID
    ) -> dict[UUID, int]:
        rankings = ProjectRanking.objects.filter(
            reviewer_id=user_id,
            competition_id=competition_id,
        )
        return {r.project_id: r.position for r in rankings}

    def get_competition_project_ids(
        self, competition_id: UUID, excluded_statuses: list[str]
    ) -> set[UUID]:
        return set(
            Competition.objects.filter(id=competition_id)
            .exclude(projects__status__in=excluded_statuses)
            .values_list("projects__id", flat=True)
        )

    def get_review_project(self, user_id: UUID, project_id: UUID) -> Project:
        has_access = CompetitionReviewer.objects.filter(
            user_id=user_id,
            competition__projects__id=project_id,
        ).exists()

        if not has_access:
            raise ReviewNotFoundError

        try:
            return (
                Project.objects.select_related("owner")
                .prefetch_related(
                    "tags",
                    "tags__category",
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
            raise ReviewNotFoundError from None
