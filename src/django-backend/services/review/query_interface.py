from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import UUID

from apps.projects.models import Project
from services.review.tally import MarginMatrix, ProjectId


@dataclass(frozen=True)
class ProjectSupport:
    """Raw signals behind one project's placement, for an admin to weigh."""

    first_place_count: int = 0
    ranked_by_count: int = 0
    mean_position: float | None = None


@dataclass(frozen=True)
class CompetitionTally:
    """The computed ordering plus everything needed to distrust it."""

    counted_ballots: int = 0
    projects: dict[ProjectId, Project] = field(default_factory=dict)
    tiers: list[list[ProjectId]] = field(default_factory=list)
    support: dict[ProjectId, ProjectSupport] = field(default_factory=dict)
    margins: MarginMatrix = field(default_factory=dict)


@dataclass(frozen=True)
class ReviewProjectItem:
    """A project as it appears on a ballot, with its images already resolved.

    Resolution happens here rather than in the router because it is only
    correct against a queryset that filtered `images` to uploaded ones — the
    rule and the prefetch it depends on belong in the same place.
    """

    project: Project
    hero_banner_url: str | None = None
    in_use_image_url: str | None = None
    category_name: str | None = None


@dataclass(frozen=True)
class ReviewerProjects:
    """One reviewer's ballot: what they ranked, and what is left to consider."""

    ranked: list[ReviewProjectItem] = field(default_factory=list)
    pool: list[ReviewProjectItem] = field(default_factory=list)


class ReviewQueryInterface(ABC):
    @abstractmethod
    def get_competition_tally(self, competition_id: UUID) -> CompetitionTally:
        """Tally the completed ballots for a competition.

        Counts only reviewers whose review is completed, over projects that are
        neither rejected nor in the ice box.
        """

    @abstractmethod
    def get_reviewer_projects(
        self, user_id: UUID, competition_id: UUID
    ) -> ReviewerProjects:
        """Split a competition's eligible projects for one reviewer.

        `ranked` is in saved position order; `pool` is in an order that is
        stable for this reviewer and uncorrelated with any other reviewer's.
        """
