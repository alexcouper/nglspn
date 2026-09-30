from hashlib import sha256
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef, Q, QuerySet

from apps.projects.models import (
    Competition,
    CompetitionReviewer,
    CompetitionStatus,
    Project,
    ProjectRanking,
    ReviewerGroup,
    ReviewStatus,
)
from services.images.django_impl.query import gallery_prefetch
from services.project.django_impl.query import (
    resolve_image_by_purpose,
    variant_url,
)
from services.review.eligibility import EXCLUDED_PROJECT_STATUSES, effective_status
from services.review.query_interface import (
    CompetitionTally,
    ReviewCompetition,
    ReviewerProjects,
    ReviewProjectItem,
    ReviewQueryInterface,
)
from services.review.tally import (
    OrderingRule,
    ProjectId,
    break_ties,
    reduce_ballots_to_margins,
    schulze_order,
    support_signals,
)


def reviewable_competitions(user_id: UUID) -> QuerySet[Competition]:
    """The competitions the user may review right now: the whole access rule.

    One queryset rather than a per-object check beside it, so the list, the
    single-competition check and the write gate cannot drift apart.
    """
    is_eligible = get_user_model().objects.filter(
        pk=user_id, is_active=True, is_system_user=False
    )
    # Exists, not a join on `members`: an OR across a many-to-many join
    # returns a competition once per member of its group.
    is_member = ReviewerGroup.members.through.objects.filter(
        reviewergroup_id=OuterRef("reviewer_group_id"), user_id=user_id
    )
    return Competition.objects.filter(
        Exists(is_eligible),
        Q(reviewer_group__includes_all_users=True) | Exists(is_member),
        status=CompetitionStatus.VOTING,
    )


def _eligible_projects(competition_id: UUID) -> list[Project]:
    return list(
        Project.objects.filter(competitions__id=competition_id).exclude(
            status__in=EXCLUDED_PROJECT_STATUSES
        )
    )


def _pool_key(user_id: UUID, competition_id: UUID, project_id: ProjectId) -> str:
    """A per-reviewer pool order that no other reviewer shares.

    Stable across reloads and devices because it is derived, not stored, and
    independent of project creation date so nothing is systematically on top.
    """
    seed = f"{user_id}:{competition_id}:{project_id}"
    return sha256(seed.encode()).hexdigest()


class DjangoReviewQuery(ReviewQueryInterface):
    def __init__(self, ordering_rule: OrderingRule = schulze_order) -> None:
        self._ordering_rule = ordering_rule

    def get_competition_tally(self, competition_id: UUID) -> CompetitionTally:
        counted_reviewer_ids = list(
            CompetitionReviewer.objects.filter(
                competition_id=competition_id,
                status=ReviewStatus.COMPLETED,
            ).values_list("user_id", flat=True)
        )

        projects = _eligible_projects(competition_id)
        eligible_ids = [p.id for p in projects]

        ballots = _ballots_by_reviewer(
            competition_id, counted_reviewer_ids, set(eligible_ids)
        )
        margins = reduce_ballots_to_margins(ballots.values(), eligible_ids)
        support = support_signals(ballots.values(), eligible_ids)
        tiers, tie_breaks = break_ties(self._ordering_rule(margins), margins, support)

        return CompetitionTally(
            counted_ballots=len(counted_reviewer_ids),
            projects={p.id: p for p in projects},
            tiers=tiers,
            support=support,
            margins=margins,
            tie_breaks=tie_breaks,
        )

    def get_reviewer_projects(
        self, user_id: UUID, competition_id: UUID
    ) -> ReviewerProjects:
        projects = list(
            Project.objects.filter(competitions__id=competition_id)
            .exclude(status__in=EXCLUDED_PROJECT_STATUSES)
            .select_related("category")
            # Filter the images here rather than in the caller:
            # `resolve_image_by_purpose` does none of its own filtering and
            # trusts whatever the prefetch handed it.
            .prefetch_related(
                gallery_prefetch(),
            )
        )

        positions = dict(
            ProjectRanking.objects.filter(
                reviewer_id=user_id,
                competition_id=competition_id,
            ).values_list("project_id", "position")
        )

        ranked = sorted(
            (p for p in projects if p.id in positions),
            key=lambda p: positions[p.id],
        )
        pool = sorted(
            (p for p in projects if p.id not in positions),
            key=lambda p: _pool_key(user_id, competition_id, p.id),
        )

        return ReviewerProjects(
            ranked=[_ballot_item(p) for p in ranked],
            pool=[_ballot_item(p) for p in pool],
        )

    def can_review(self, user_id: UUID, competition_id: UUID) -> bool:
        return reviewable_competitions(user_id).filter(pk=competition_id).exists()

    def review_competitions_for(self, user_id: UUID) -> list[ReviewCompetition]:
        row_statuses = dict(
            CompetitionReviewer.objects.filter(user_id=user_id).values_list(
                "competition_id", "status"
            )
        )
        reviewable_ids = set(
            reviewable_competitions(user_id).values_list("pk", flat=True)
        )
        competitions = Competition.objects.filter(
            pk__in=reviewable_ids | row_statuses.keys()
        ).order_by("-start_date")
        return [
            ReviewCompetition(
                competition=competition,
                status=effective_status(
                    row_statuses.get(competition.pk), competition.status
                ),
                can_write=competition.pk in reviewable_ids,
            )
            for competition in competitions
        ]

    def get_review_competition(
        self, user_id: UUID, competition_id: UUID
    ) -> ReviewCompetition | None:
        competition = Competition.objects.filter(pk=competition_id).first()
        if competition is None:
            return None
        row_status = (
            CompetitionReviewer.objects.filter(
                user_id=user_id, competition_id=competition_id
            )
            .values_list("status", flat=True)
            .first()
        )
        can_write = self.can_review(user_id, competition_id)
        if not can_write and row_status is None:
            return None
        return ReviewCompetition(
            competition=competition,
            status=effective_status(row_status, competition.status),
            can_write=can_write,
        )

    def can_view_review_project(self, user_id: UUID, project_id: UUID) -> bool:
        return (
            Competition.objects.filter(projects__id=project_id)
            .filter(
                Q(pk__in=reviewable_competitions(user_id).values("pk"))
                | Q(reviewers__user_id=user_id)
            )
            .exists()
        )


def _ballot_item(project: Project) -> ReviewProjectItem:
    """Resolve a project's ballot presentation the way the listing does.

    `resolve_image_by_purpose` does no `upload_status` filtering of its own, so
    this is only correct on a project loaded by `get_reviewer_projects`, whose
    prefetch is narrowed to uploaded images.
    """
    return ReviewProjectItem(
        project=project,
        hero_banner_url=variant_url(
            resolve_image_by_purpose(project, "hero_banner"), "large"
        ),
        in_use_image_url=variant_url(
            resolve_image_by_purpose(project, "in_use"), "medium"
        ),
        category_name=project.category.name if project.category else None,
    )


def _ballots_by_reviewer(
    competition_id: UUID,
    reviewer_ids: list[UUID],
    eligible_ids: set[ProjectId],
) -> dict[UUID, list[ProjectId]]:
    """One ballot per counted reviewer, in position order.

    A reviewer who completed their review without ranking anything still has a
    ballot; it is simply empty.
    """
    ballots: dict[UUID, list[ProjectId]] = {rid: [] for rid in reviewer_ids}

    rows = (
        ProjectRanking.objects.filter(
            competition_id=competition_id,
            reviewer_id__in=reviewer_ids,
        )
        .order_by("position")
        .values_list("reviewer_id", "project_id")
    )
    for reviewer_id, project_id in rows:
        if project_id in eligible_ids:
            ballots[reviewer_id].append(project_id)

    return ballots
