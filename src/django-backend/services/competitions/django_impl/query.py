import uuid

from django.db.models import Count, Prefetch
from django.db.models.functions import Lower

from apps.projects.models import (
    Competition,
    CompetitionStatus,
    Project,
    ProjectImage,
    ProjectStatus,
)
from services.competitions.exceptions import CompetitionNotFoundError
from services.competitions.query_interface import (
    CompetitionDetailItem,
    CompetitionHighlightItem,
    CompetitionOverviewItem,
    CompetitionQueryInterface,
)
from services.project.django_impl import to_list_item


class DjangoCompetitionQuery(CompetitionQueryInterface):
    def list_all(self) -> list[CompetitionOverviewItem]:
        competitions = Competition.objects.prefetch_related("projects").all()
        return [
            CompetitionOverviewItem(
                competition=c,
                project_count=c.projects.count(),
                pending_projects_count=c.projects.filter(
                    status=ProjectStatus.PENDING
                ).count(),
            )
            for c in competitions
        ]

    def list_with_projects(self) -> list[CompetitionDetailItem]:
        competitions = (
            Competition.objects.select_related("winner")
            .prefetch_related(
                "projects",
                "projects__images",
                "projects__tags",
                "winner__images",
                "winner__tags",
            )
            .all()
        )
        pending_count = self.count_pending_projects()
        return [
            self._to_detail_item(c, pending_projects_count=pending_count)
            for c in competitions
        ]

    def get_by_id_or_slug(self, identifier: str) -> CompetitionDetailItem:
        queryset = Competition.objects.select_related("winner").prefetch_related(
            "projects",
            "projects__images",
            "projects__tags",
            "winner__images",
            "winner__tags",
        )
        try:
            uuid.UUID(identifier)
            competition = queryset.get(id=identifier)
        except ValueError:
            try:
                competition = queryset.get(slug=identifier)
            except Competition.DoesNotExist:
                raise CompetitionNotFoundError from None
        except Competition.DoesNotExist:
            raise CompetitionNotFoundError from None

        return self._to_detail_item(competition)

    def list_highlights(self) -> list[CompetitionHighlightItem]:
        base_qs = Competition.objects.annotate(project_count=Count("projects"))

        active = list(
            base_qs.filter(
                status__in=[
                    CompetitionStatus.ACCEPTING_APPLICATIONS,
                    CompetitionStatus.VOTING,
                ]
            ).order_by("-start_date")
        )
        recent = (
            base_qs.filter(status=CompetitionStatus.CLOSED)
            .order_by("-voting_end_date", "-submission_deadline")
            .first()
        )

        results = [
            CompetitionHighlightItem(competition=c, project_count=c.project_count)
            for c in active
        ]
        if recent:
            results.append(
                CompetitionHighlightItem(
                    competition=recent, project_count=recent.project_count
                )
            )

        return results

    def count_pending_projects(self) -> int:
        return Project.objects.filter(status=ProjectStatus.PENDING).count()

    def _to_detail_item(
        self,
        competition: Competition,
        *,
        pending_projects_count: int | None = None,
    ) -> CompetitionDetailItem:
        approved_projects = list(
            competition.projects.filter(status=ProjectStatus.APPROVED)
            .order_by(Lower("title"))
            .prefetch_related(
                Prefetch(
                    "images",
                    queryset=ProjectImage.objects.filter(
                        upload_status="uploaded"
                    ).prefetch_related("variants"),
                ),
                "tags__category",
                "won_competitions",
            )
        )
        project_items = [to_list_item(p) for p in approved_projects]
        winner_item = to_list_item(competition.winner) if competition.winner else None

        if pending_projects_count is None:
            pending_projects_count = competition.projects.filter(
                status=ProjectStatus.PENDING
            ).count()

        return CompetitionDetailItem(
            competition=competition,
            project_items=project_items,
            winner_item=winner_item,
            project_count=competition.projects.count(),
            pending_projects_count=pending_projects_count,
        )
