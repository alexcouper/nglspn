from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.projects.models import (
    CompetitionEntry,
    ContributorRole,
    EntrySource,
    Project,
    ProjectContributor,
    ProjectImage,
    ProjectStatus,
)
from apps.projects.slugs import assign_unique_slug
from apps.tags.models import Tag, TagStatus
from apps.users.seed import COMMUNITY_USER_ID
from services.project.exceptions import (
    CompetitionEntryConflictError,
    InvalidCompetitionError,
    InvalidProjectStateError,
    InvalidTagsError,
    ProjectNotFoundError,
    PublishPreconditionsError,
)
from services.project.handler_interface import ProjectHandlerInterface

from .query import DjangoProjectQuery, get_title_from_url, stamp_competition_standing

_query = DjangoProjectQuery()

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet

    from services.project.handler_interface import (
        CreateProjectInput,
        UpdateProjectInput,
    )


def _validate_tags(tag_ids: list[UUID]) -> QuerySet[Tag]:
    valid_tags = Tag.objects.filter(id__in=tag_ids).exclude(status=TagStatus.REJECTED)
    if len(tag_ids) != valid_tags.count():
        msg = "One or more tag IDs are invalid or rejected"
        raise InvalidTagsError(msg)
    return valid_tags


def _enqueue_new_project_notification(project: Project) -> None:
    from api.tasks import email as email_tasks  # noqa: PLC0415

    try:
        email_tasks.send_new_project_notification.enqueue(str(project.id))
    except Exception:
        logger.exception(
            "Failed to enqueue new-project notification for %s", project.id
        )


def _get_editable_project(project_id: UUID, user_id: UUID) -> Project:
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        raise ProjectNotFoundError from None
    if not _query.user_can_edit(project.id, user_id):
        raise ProjectNotFoundError
    return project


class DjangoProjectHandler(ProjectHandlerInterface):
    def create(self, data: CreateProjectInput) -> Project:
        valid_tags = None
        if data.tag_ids:
            valid_tags = _validate_tags(data.tag_ids)

        project_fields: dict[str, Any] = {
            "creator_id": data.owner_id,
            "website_url": data.website_url,
        }
        for field in (
            "title",
            "tagline",
            "description",
            "long_description",
            "github_url",
            "demo_url",
            "tech_stack",
        ):
            value = getattr(data, field)
            if value is not None:
                project_fields[field] = value

        if not project_fields.get("title"):
            project_fields["title"] = get_title_from_url(data.website_url)

        with transaction.atomic():
            project = Project.objects.create(**project_fields)
            # FK constant avoids a DB roundtrip; if the seed migration never
            # ran, the FK insert will fail loudly.
            owner_user_id = (
                COMMUNITY_USER_ID if data.is_community_tipoff else data.owner_id
            )
            ProjectContributor.objects.create(
                project=project,
                user_id=owner_user_id,
                role=ContributorRole.OWNER,
                full_edit=True,
            )
            if data.is_community_tipoff:
                ProjectContributor.objects.create(
                    project=project,
                    user_id=data.owner_id,
                    role=ContributorRole.TIPSTER,
                    full_edit=True,
                )

            if valid_tags is not None:
                project.tags.set(valid_tags)

        return stamp_competition_standing(project)

    def update(
        self, project_id: UUID, owner_id: UUID, data: UpdateProjectInput
    ) -> Project:
        project = _get_editable_project(project_id, owner_id)

        valid_tags = _validate_tags(data.tag_ids) if data.tag_ids else None

        update_fields: dict[str, Any] = {"website_url": data.website_url}
        for field in (
            "title",
            "tagline",
            "description",
            "long_description",
            "github_url",
            "demo_url",
            "tech_stack",
        ):
            value = getattr(data, field)
            if value is not None:
                update_fields[field] = value

        if not update_fields.get("title"):
            parsed_url = urlparse(data.website_url)
            domain = parsed_url.netloc or parsed_url.path
            domain = domain.replace("www.", "")
            update_fields["title"] = domain or "Untitled Project"

        for field, value in update_fields.items():
            setattr(project, field, value)

        if project.status == ProjectStatus.REJECTED:
            project.status = ProjectStatus.PENDING
            project.rejection_reason = None

        project.save()

        if valid_tags is not None:
            project.tags.set(valid_tags)
        else:
            project.tags.clear()

        return stamp_competition_standing(project)

    def delete(self, project_id: UUID, owner_id: UUID) -> None:
        project = _get_editable_project(project_id, owner_id)
        project.delete()

    def resubmit(self, project_id: UUID, owner_id: UUID) -> Project:
        project = _get_editable_project(project_id, owner_id)

        if project.status != ProjectStatus.REJECTED:
            msg = "Only rejected projects can be resubmitted"
            raise InvalidProjectStateError(msg)

        project.status = ProjectStatus.PENDING
        project.rejection_reason = None
        project.save()

        return stamp_competition_standing(project)

    def publish(self, project_id: UUID, owner_id: UUID) -> Project:
        project = _get_editable_project(project_id, owner_id)

        if project.status != ProjectStatus.DRAFT:
            msg = "Only draft projects can be published"
            raise InvalidProjectStateError(msg)

        missing = _publish_preconditions_missing(project)
        if missing:
            raise PublishPreconditionsError(missing)

        with transaction.atomic():
            assign_unique_slug(project)

            now = timezone.now()
            project.status = ProjectStatus.PENDING
            project.published_at = now
            project.submission_month = now.strftime("%Y-%m")
            project.save(
                update_fields=[
                    "status",
                    "published_at",
                    "submission_month",
                    "updated_at",
                ]
            )

        # Publishing enters no competition. Entry is its own request against
        # its own endpoint, naming the competition — see enter_competition().

        _enqueue_new_project_notification(project)

        return stamp_competition_standing(project)

    def enter_competition(
        self, project_id: UUID, competition_id: UUID, user_id: UUID
    ) -> Project:
        project = _get_editable_project(project_id, user_id)

        if project.status == ProjectStatus.DRAFT:
            msg = "A draft must be published before it can enter a competition"
            raise InvalidProjectStateError(msg)

        # The lock is on the project, not the competition, because the rule
        # being protected is about the project: one entry per series. Two
        # requests naming two rounds of the same series would otherwise both
        # read a standing without the other's entry and both insert, and no
        # unique constraint can catch that — the pair the database enforces is
        # (competition, project), and those two rows differ.
        #
        # SQLite ignores `select_for_update`, so this buys nothing under the
        # test settings; the deployment runs Postgres, where it serialises.
        with transaction.atomic():
            locked = Project.objects.select_for_update().get(pk=project.pk)
            return self._create_entry(locked, competition_id, user_id)

    def _create_entry(
        self, project: Project, competition_id: UUID, user_id: UUID
    ) -> Project:
        """Caller holds the lock on `project`. Re-reads everything it decides
        on, so a standing that went stale while the user looked at it loses."""
        if CompetitionEntry.objects.filter(
            project=project, competition_id=competition_id
        ).exists():
            # Ahead of the opportunity lookup: an entered round is deliberately
            # absent from `opportunities`, so without this the caller would be
            # told the round is not accepting applications, which is false.
            msg = "This project is already entered in that competition"
            raise CompetitionEntryConflictError(msg)

        # Re-evaluated here rather than trusted from the caller: the round may
        # have closed, or somebody may have entered the project, since the
        # page that offered the control was rendered.
        standing = _query.competition_standing(project)
        opportunity = next(
            (
                candidate
                for candidate in standing.opportunities
                if candidate.competition.id == competition_id
            ),
            None,
        )
        if opportunity is None:
            msg = "That competition is not accepting applications"
            raise InvalidCompetitionError(msg)
        if not opportunity.eligible:
            msg = f"This project cannot enter that competition: {opportunity.reason}"
            raise InvalidCompetitionError(msg)

        try:
            # The inner atomic is required, not decorative: without it the
            # failed insert leaves the surrounding transaction unusable, so the
            # caller's next query dies instead of getting its 409.
            with transaction.atomic():
                CompetitionEntry.objects.create(
                    competition=opportunity.competition,
                    project=project,
                    entered_via=EntrySource.MANUAL,
                    entered_by_id=user_id,
                )
        except IntegrityError as exc:
            msg = "This project is already entered in that competition"
            raise CompetitionEntryConflictError(msg) from exc

        return stamp_competition_standing(project)


def _publish_preconditions_missing(project: Project) -> list[str]:
    missing: list[str] = []
    if not (project.title and project.title.strip()):
        missing.append("title")
    if not (project.description and project.description.strip()):
        missing.append("description")
    has_main_image = (
        ProjectImage.objects.uploaded().filter(project=project, is_main=True).exists()
    )
    if not has_main_image:
        missing.append("main_image")
    return missing
