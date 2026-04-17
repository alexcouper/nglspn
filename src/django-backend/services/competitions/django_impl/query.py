from __future__ import annotations

import uuid

from django.db.models import Count, QuerySet

from apps.projects.models import Competition, CompetitionStatus, Project, ProjectStatus
from services.competitions.exceptions import CompetitionNotFoundError
from services.competitions.query_interface import (
    CompetitionHighlight,
    CompetitionQueryInterface,
)


def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    else:
        return True


def _with_projects_queryset() -> QuerySet[Competition]:
    return Competition.objects.select_related("winner").prefetch_related(
        "projects",
        "projects__images",
        "projects__images__variants",
        "projects__tags",
        "projects__tags__category",
        "projects__won_competitions",
        "winner__images",
        "winner__images__variants",
        "winner__tags",
        "winner__tags__category",
        "winner__won_competitions",
    )


class DjangoCompetitionQuery(CompetitionQueryInterface):
    def list_all(self) -> QuerySet[Competition]:
        return Competition.objects.prefetch_related("projects").all()

    def list_with_projects(self) -> QuerySet[Competition]:
        return _with_projects_queryset().all()

    def get_by_id_or_slug(self, identifier: str) -> Competition:
        queryset = _with_projects_queryset()
        lookup = (
            {"id": identifier} if _is_valid_uuid(identifier) else {"slug": identifier}
        )
        try:
            return queryset.get(**lookup)
        except Competition.DoesNotExist:
            raise CompetitionNotFoundError from None

    def list_highlights(self) -> list[CompetitionHighlight]:
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

        highlights = [
            CompetitionHighlight(competition=c, project_count=c.project_count)
            for c in active
        ]
        if recent is not None:
            highlights.append(
                CompetitionHighlight(
                    competition=recent, project_count=recent.project_count
                )
            )
        return highlights

    def count_pending_projects(self) -> int:
        return Project.objects.filter(status=ProjectStatus.PENDING).count()
