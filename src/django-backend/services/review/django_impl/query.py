from collections import defaultdict
from collections.abc import Iterable
from hashlib import sha256
from uuid import UUID

from apps.projects.models import (
    CompetitionReviewer,
    Project,
    ProjectRanking,
    ProjectStatus,
    ReviewStatus,
)
from services.review.query_interface import (
    CompetitionTally,
    ProjectSupport,
    ReviewerProjects,
    ReviewQueryInterface,
)
from services.review.tally import (
    Ballot,
    OrderingRule,
    ProjectId,
    reduce_ballots_to_margins,
    schulze_order,
)

EXCLUDED_PROJECT_STATUSES = [ProjectStatus.REJECTED, ProjectStatus.ICE_BOX]


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

        return CompetitionTally(
            counted_ballots=len(counted_reviewer_ids),
            projects={p.id: p for p in projects},
            tiers=self._ordering_rule(margins),
            support=_support_signals(ballots.values(), eligible_ids),
            margins=margins,
        )

    def get_reviewer_projects(
        self, user_id: UUID, competition_id: UUID
    ) -> ReviewerProjects:
        projects = list(
            Project.objects.filter(competitions__id=competition_id)
            .exclude(status__in=EXCLUDED_PROJECT_STATUSES)
            .prefetch_related("images", "images__variants")
        )

        positions = dict(
            ProjectRanking.objects.filter(
                reviewer_id=user_id,
                competition_id=competition_id,
            ).values_list("project_id", "position")
        )

        return ReviewerProjects(
            ranked=sorted(
                (p for p in projects if p.id in positions),
                key=lambda p: positions[p.id],
            ),
            pool=sorted(
                (p for p in projects if p.id not in positions),
                key=lambda p: _pool_key(user_id, competition_id, p.id),
            ),
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


def _support_signals(
    ballots: Iterable[Ballot], eligible_ids: list[ProjectId]
) -> dict[ProjectId, ProjectSupport]:
    """First-place count, ranked-by count and mean position among rankers.

    Positions are the reviewer's own contiguous ordering, so a project ranked
    second on a two-project ballot has position 2 regardless of how many
    projects the reviewer skipped.
    """
    first_place: dict[ProjectId, int] = defaultdict(int)
    ranked_by: dict[ProjectId, int] = defaultdict(int)
    position_total: dict[ProjectId, int] = defaultdict(int)

    for ballot in ballots:
        for position, project_id in enumerate(ballot, start=1):
            ranked_by[project_id] += 1
            position_total[project_id] += position
            if position == 1:
                first_place[project_id] += 1

    return {
        project_id: ProjectSupport(
            first_place_count=first_place[project_id],
            ranked_by_count=ranked_by[project_id],
            mean_position=(
                position_total[project_id] / ranked_by[project_id]
                if ranked_by[project_id]
                else None
            ),
        )
        for project_id in eligible_ids
    }
