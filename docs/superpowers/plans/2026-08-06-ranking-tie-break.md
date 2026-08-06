# Ranking Tie-Break Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve tied ranks in the competition tally with a fixed four-rung ladder, and explain the whole method — ranking and tiebreak — in prose on the admin results page.

**Architecture:** Tiebreaking is a pure stage applied to the ordering rule's output, not part of it: `OrderingRule` stays `(margins) -> tiers`, and `break_ties(tiers, margins, support)` runs after. Support signals move from `django_impl/query.py` into `tally.py` so the ladder is testable without a database. `DjangoReviewQuery.get_competition_tally` calls both and passes the rung that decided each placement through to the template.

**Tech Stack:** Python 3.12, Django 4.2, pytest + PyHamcrest, `uv`, Ruff. Django admin templates (plain HTML, inline styles).

## Global Constraints

- Spec: [`docs/superpowers/specs/2026-08-06-ranking-tie-break-design.md`](../specs/2026-08-06-ranking-tie-break-design.md). Read it before starting.
- **Use `jj`, not `git`.** Commit with `jj commit -m "..."`. Check state with `jj status`.
- Run all commands from `src/django-backend/`.
- Lint with `uv run ruff check . && uv run ruff format .` before every commit. CI runs `make lint`.
- Tests: `uv run pytest <path> -q`. Full suite: `make test`.
- `tally.py` stays pure — no Django, no ORM imports, ever.
- Rung display names are fixed strings, used verbatim in both code and template: `least-bad worst defeat`, `ranked by more reviewers`, `better mean position`, `more first-place votes`.
- No migration, no API change. No endpoint exposes the tally.
- Do not add joint-winner schema. `Competition.winner` stays a single FK.

---

### Task 1: Move support signals into the pure tally module

The ladder needs support signals and must stay database-free. `_support_signals` is already ORM-free but sits in the Django implementation; `ProjectSupport` sits in `query_interface.py`. Both move to `tally.py`. No behaviour change.

**Files:**
- Modify: `services/review/tally.py`
- Modify: `services/review/query_interface.py:1-16`
- Modify: `services/review/django_impl/query.py:1-32` (imports), `:172-203` (delete `_support_signals`)
- Test: `services/review/test_tally.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `ProjectSupport` (frozen dataclass: `first_place_count: int = 0`, `ranked_by_count: int = 0`, `mean_position: float | None = None`) and `support_signals(ballots: Iterable[Ballot], eligible_project_ids: Collection[ProjectId]) -> dict[ProjectId, ProjectSupport]`, both importable from `services.review.tally`.

- [ ] **Step 1: Write the failing test**

Append to `services/review/test_tally.py`:

```python
class TestSupportSignals:
    def test_counts_first_places_and_rankers(self) -> None:
        support = support_signals([[A, B], [B, A], [A]], ALL_FOUR)

        assert_that(support[A].first_place_count, equal_to(2))
        assert_that(support[A].ranked_by_count, equal_to(3))
        assert_that(support[B].first_place_count, equal_to(1))

    def test_mean_position_covers_only_the_ballots_that_ranked_it(self) -> None:
        support = support_signals([[A, B], [B, A], [A]], ALL_FOUR)

        # A sits at 1, 2 and 1 -> 4/3; B at 2 and 1 -> 3/2.
        assert_that(support[A].mean_position, equal_to(4 / 3))
        assert_that(support[B].mean_position, equal_to(3 / 2))

    def test_a_project_nobody_ranked_has_no_mean_position(self) -> None:
        support = support_signals([[A]], ALL_FOUR)

        assert_that(support[D].ranked_by_count, equal_to(0))
        assert_that(support[D].mean_position, equal_to(None))
```

Add `support_signals` to the existing import block at the top of the file:

```python
from services.review.tally import (
    MarginMatrix,
    ProjectId,
    reduce_ballots_to_margins,
    schulze_order,
    support_signals,
)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest services/review/test_tally.py -q -k SupportSignals`
Expected: FAIL — `ImportError: cannot import name 'support_signals'`

- [ ] **Step 3: Add `ProjectSupport` and `support_signals` to `tally.py`**

Extend the imports at the top of `services/review/tally.py`:

```python
from collections import defaultdict
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID
```

Add after the `MarginMatrix` / `Ballot` type aliases:

```python
@dataclass(frozen=True)
class ProjectSupport:
    """Raw signals behind one project's placement, for an admin to weigh."""

    first_place_count: int = 0
    ranked_by_count: int = 0
    mean_position: float | None = None
```

Add at the end of the file:

```python
def support_signals(
    ballots: Iterable[Ballot],
    eligible_project_ids: Collection[ProjectId],
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
        for project_id in eligible_project_ids
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest services/review/test_tally.py -q -k SupportSignals`
Expected: PASS (3 passed)

- [ ] **Step 5: Point `query_interface.py` at the new home**

In `services/review/query_interface.py`, delete the `ProjectSupport` class definition and change the import line to:

```python
from services.review.tally import MarginMatrix, ProjectId, ProjectSupport
```

`ProjectSupport` stays importable from `query_interface` because `CompetitionTally.support` still annotates with it — existing importers do not change.

- [ ] **Step 6: Delete the duplicate from the Django implementation**

In `services/review/django_impl/query.py`:

1. Delete the whole `_support_signals` function.
2. Change the `services.review.tally` import block to:

```python
from services.review.tally import (
    OrderingRule,
    ProjectId,
    reduce_ballots_to_margins,
    schulze_order,
    support_signals,
)
```

3. In `get_competition_tally`, change `support=_support_signals(...)` to `support=support_signals(ballots.values(), eligible_ids)`.
4. Remove the now-unused imports: `from collections import defaultdict`, `from collections.abc import Iterable`, `Ballot` from the tally import, and `ProjectSupport` from the `query_interface` import.

- [ ] **Step 7: Verify nothing regressed**

Run: `uv run ruff check --fix . && uv run ruff format . && uv run pytest services/review/ tests/test_voting_results.py -q`
Expected: PASS, no ruff errors. If ruff reports an unused import you missed, remove it.

- [ ] **Step 8: Commit**

```bash
jj commit -m "review: move support signals into the pure tally module"
```

---

### Task 2: The ladder, with the minimax rung only

Ladder machinery plus the first and most important rung. A reviewer can accept this and still argue about the positional rungs in Task 3.

**Files:**
- Modify: `services/review/tally.py`
- Test: `services/review/test_tally.py`

**Interfaces:**
- Consumes: `ProjectSupport`, `support_signals` from Task 1.
- Produces:
  - `TieBreak` — frozen dataclass, fields `rung: str` and `tied_with: tuple[ProjectId, ...]`.
  - `break_ties(tiers: list[list[ProjectId]], margins: MarginMatrix, support: dict[ProjectId, ProjectSupport]) -> tuple[list[list[ProjectId]], dict[ProjectId, TieBreak]]`.
  - `TIE_BREAK_RUNGS: list[tuple[str, ScoreRung]]` — the ordered ladder.

Note this refines the spec, which sketched the reason map as `dict[ProjectId, str]`. `TieBreak` also carries who the project was tied with, which the page footnote needs. Update the spec's code block to match at the end of Task 5.

- [ ] **Step 1: Write the failing test**

Append to `services/review/test_tally.py`:

```python
class TestBreakTiesByWorstDefeat:
    def test_a_singleton_tier_is_left_alone(self) -> None:
        margins = margin_matrix({(A, B): 1})

        tiers, reasons = break_ties([[A], [B]], margins, no_support([A, B]))

        assert_that(tiers, equal_to([[A], [B]]))
        assert_that(reasons, equal_to({}))

    def test_the_project_that_won_head_to_head_is_placed_first(self) -> None:
        # Schulze could not separate them, but A beat B directly.
        margins = margin_matrix({(A, B): 1})

        tiers, reasons = break_ties([[A, B]], margins, no_support([A, B]))

        assert_that(tiers, equal_to([[A], [B]]))
        assert_that(reasons[A].rung, equal_to("least-bad worst defeat"))
        assert_that(reasons[A].tied_with, equal_to((B,)))

    def test_a_three_way_loop_is_settled_by_the_least_bad_defeat(self) -> None:
        # The worked example printed on the admin page: A>B by 2, B>C by 4,
        # C>A by 6. Nobody is unbeaten; B lost by least, so B is placed first.
        margins = margin_matrix({(A, B): 2, (B, C): 4, (C, A): 6})

        tiers, reasons = break_ties([[A, B, C]], margins, no_support([A, B, C]))

        assert_that([t[0] for t in tiers], equal_to([B, C, A]))
        assert_that(reasons[B].rung, equal_to("least-bad worst defeat"))

    def test_a_dead_level_pair_is_left_tied_when_no_rung_can_separate_it(
        self,
    ) -> None:
        margins = margin_matrix({(A, B): 0})

        tiers, reasons = break_ties([[A, B]], margins, no_support([A, B]))

        assert_that(tiers, equal_to([[A, B]]))
        assert_that(reasons, equal_to({}))
```

Add this helper next to the existing `margin_matrix` helper in the same file:

```python
def no_support(project_ids: list[ProjectId]) -> dict[ProjectId, ProjectSupport]:
    """Support signals that separate nothing, so only the margins decide."""
    return {p: ProjectSupport(0, 0, None) for p in project_ids}
```

Extend the import block:

```python
from services.review.tally import (
    MarginMatrix,
    ProjectId,
    ProjectSupport,
    break_ties,
    reduce_ballots_to_margins,
    schulze_order,
    support_signals,
)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest services/review/test_tally.py -q -k BreakTiesByWorstDefeat`
Expected: FAIL — `ImportError: cannot import name 'break_ties'`

- [ ] **Step 3: Implement the ladder with one rung**

Add to `services/review/tally.py`. Put `ScoreRung` and `TieBreak` near the other type declarations, and the rest at the end of the file:

```python
# A rung scores each tied project; higher is better, and equal scores stay tied.
ScoreRung = Callable[
    [list[ProjectId], MarginMatrix, dict[ProjectId, "ProjectSupport"]],
    dict[ProjectId, float],
]

# Score for a project a rung cannot rate at all. Sorts last.
_WORST = float("-inf")


@dataclass(frozen=True)
class TieBreak:
    """Why a project that shared a tier now has a rank of its own."""

    rung: str
    tied_with: tuple[ProjectId, ...]
```

`Callable` needs adding to the `collections.abc` import:

```python
from collections.abc import Callable, Collection, Iterable, Sequence
```

Then the rung and the ladder:

```python
def _worst_defeat(
    tied: list[ProjectId],
    margins: MarginMatrix,
    support: dict[ProjectId, ProjectSupport],  # noqa: ARG001
) -> dict[ProjectId, float]:
    """Each project's biggest losing margin *within the tied group*.

    Least bad wins. For a pair this is simply the head-to-head result; for a
    loop it is the only comparison-based answer available, because no project
    in a loop is unbeaten.
    """
    return {a: min(margins[a][b] for b in tied if b != a) for a in tied}


TIE_BREAK_RUNGS: list[tuple[str, ScoreRung]] = [
    ("least-bad worst defeat", _worst_defeat),
]


def _separate(
    tied: list[ProjectId],
    margins: MarginMatrix,
    support: dict[ProjectId, ProjectSupport],
    rungs: list[tuple[str, ScoreRung]],
) -> list[tuple[list[ProjectId], str | None]]:
    """Split a tied group into ordered subgroups, best first.

    Each subgroup is paired with the rung that separated it, or None when the
    ladder ran out and the group is genuinely indistinguishable.
    """
    if len(tied) == 1 or not rungs:
        return [(list(tied), None)]

    (name, score), *rest = rungs
    scores = score(tied, margins, support)
    groups = [
        [p for p in tied if scores[p] == value]
        for value in sorted(set(scores.values()), reverse=True)
    ]
    if len(groups) == 1:
        return _separate(tied, margins, support, rest)

    separated: list[tuple[list[ProjectId], str | None]] = []
    for group in groups:
        for subgroup, deeper_name in _separate(group, margins, support, rest):
            separated.append((subgroup, deeper_name or name))
    return separated


def break_ties(
    tiers: list[list[ProjectId]],
    margins: MarginMatrix,
    support: dict[ProjectId, ProjectSupport],
) -> tuple[list[list[ProjectId]], dict[ProjectId, TieBreak]]:
    """Split tied tiers as far as the ladder allows.

    Returns the new tiers and, for each project whose placement came from a
    tiebreak, which rung decided it and who it had been tied with.
    """
    resolved: list[list[ProjectId]] = []
    reasons: dict[ProjectId, TieBreak] = {}

    for tier in tiers:
        if len(tier) == 1:
            resolved.append(list(tier))
            continue

        for group, rung in _separate(list(tier), margins, support, TIE_BREAK_RUNGS):
            resolved.append(group)
            if rung is None:
                continue
            for project_id in group:
                reasons[project_id] = TieBreak(
                    rung=rung,
                    tied_with=tuple(p for p in tier if p != project_id),
                )

    return resolved, reasons
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest services/review/test_tally.py -q -k BreakTies`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
uv run ruff check --fix . && uv run ruff format . && uv run pytest services/review/test_tally.py -q
jj commit -m "review: break tied ranks by least-bad worst defeat"
```

---

### Task 3: The remaining three rungs

Breadth, mean position and first places. They come after minimax so they only ever see projects the margins could not separate — see the spec for why that ordering is not negotiable.

**Files:**
- Modify: `services/review/tally.py`
- Test: `services/review/test_tally.py`

**Interfaces:**
- Consumes: `TIE_BREAK_RUNGS`, `_separate`, `break_ties`, `_WORST`, `ScoreRung` from Task 2.
- Produces: `TIE_BREAK_RUNGS` extended to four entries, in this exact order: `least-bad worst defeat`, `ranked by more reviewers`, `better mean position`, `more first-place votes`.

- [ ] **Step 1: Write the failing test**

Append to `services/review/test_tally.py`:

```python
def support_for(
    values: dict[ProjectId, tuple[int, int, float | None]],
) -> dict[ProjectId, ProjectSupport]:
    """(first places, ranked by, mean position) per project."""
    return {
        p: ProjectSupport(first_place_count=f, ranked_by_count=r, mean_position=m)
        for p, (f, r, m) in values.items()
    }


class TestBreakTiesByTheLaterRungs:
    def test_breadth_separates_when_the_margins_cannot(self) -> None:
        margins = margin_matrix({(A, B): 0})
        support = support_for({A: (0, 4, 2.0), B: (0, 9, 2.0)})

        tiers, reasons = break_ties([[A, B]], margins, support)

        assert_that(tiers, equal_to([[B], [A]]))
        assert_that(reasons[B].rung, equal_to("ranked by more reviewers"))

    def test_a_lower_mean_position_wins(self) -> None:
        margins = margin_matrix({(A, B): 0})
        support = support_for({A: (0, 5, 3.4), B: (0, 5, 2.1)})

        tiers, reasons = break_ties([[A, B]], margins, support)

        assert_that(tiers, equal_to([[B], [A]]))
        assert_that(reasons[B].rung, equal_to("better mean position"))

    def test_a_project_nobody_ranked_sorts_last_on_mean_position(self) -> None:
        margins = margin_matrix({(A, B): 0})
        support = support_for({A: (0, 0, None), B: (0, 5, 7.9)})

        tiers, _reasons = break_ties([[A, B]], margins, support)

        assert_that(tiers, equal_to([[B], [A]]))

    def test_first_places_decide_only_when_everything_else_is_level(self) -> None:
        margins = margin_matrix({(A, B): 0})
        support = support_for({A: (1, 5, 2.0), B: (4, 5, 2.0)})

        tiers, reasons = break_ties([[A, B]], margins, support)

        assert_that(tiers, equal_to([[B], [A]]))
        assert_that(reasons[B].rung, equal_to("more first-place votes"))

    def test_the_margins_outrank_first_places_when_they_disagree(self) -> None:
        # The Hvitlaukur rank-5 shape: the project with far more 1st places
        # lost head to head, and the head-to-head result wins.
        margins = margin_matrix({(A, B): 1})
        support = support_for({A: (1, 11, 5.18), B: (5, 11, 4.45)})

        tiers, reasons = break_ties([[A, B]], margins, support)

        assert_that(tiers, equal_to([[A], [B]]))
        assert_that(reasons[A].rung, equal_to("least-bad worst defeat"))

    def test_a_tier_survives_when_every_rung_is_level(self) -> None:
        margins = margin_matrix({(A, B): 0})
        support = support_for({A: (2, 5, 1.5), B: (2, 5, 1.5)})

        tiers, reasons = break_ties([[A, B]], margins, support)

        assert_that(tiers, equal_to([[A, B]]))
        assert_that(reasons, equal_to({}))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest services/review/test_tally.py -q -k TestBreakTiesByTheLaterRungs`
Expected: FAIL — the first four tests fail with `[[A, B]] != [[B], [A]]`, because only the minimax rung exists and it cannot separate a zero margin.

- [ ] **Step 3: Add the three rungs**

In `services/review/tally.py`, add after `_worst_defeat`:

```python
def _breadth(
    tied: list[ProjectId],
    margins: MarginMatrix,  # noqa: ARG001
    support: dict[ProjectId, ProjectSupport],
) -> dict[ProjectId, float]:
    """How many reviewers ranked the project at all. More is better."""
    return {a: support[a].ranked_by_count for a in tied}


def _mean_position(
    tied: list[ProjectId],
    margins: MarginMatrix,  # noqa: ARG001
    support: dict[ProjectId, ProjectSupport],
) -> dict[ProjectId, float]:
    """Mean position among rankers, negated because position 1 is best.

    A project nobody ranked has no mean position and sorts last.
    """
    scores: dict[ProjectId, float] = {}
    for a in tied:
        mean = support[a].mean_position
        scores[a] = _WORST if mean is None else -mean
    return scores


def _first_places(
    tied: list[ProjectId],
    margins: MarginMatrix,  # noqa: ARG001
    support: dict[ProjectId, ProjectSupport],
) -> dict[ProjectId, float]:
    """How many reviewers put the project top. More is better."""
    return {a: support[a].first_place_count for a in tied}
```

Replace `TIE_BREAK_RUNGS` with:

```python
# Order matters and is argued in the design doc: the margin-based rung leads so
# the ladder can never contradict the vote, and the positional rungs come last
# because they measure how much reviewers preferred a project rather than how
# often — the scoring this tally deliberately moved away from.
TIE_BREAK_RUNGS: list[tuple[str, ScoreRung]] = [
    ("least-bad worst defeat", _worst_defeat),
    ("ranked by more reviewers", _breadth),
    ("better mean position", _mean_position),
    ("more first-place votes", _first_places),
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest services/review/test_tally.py -q`
Expected: PASS, all tests in the file.

- [ ] **Step 5: Commit**

```bash
uv run ruff check --fix . && uv run ruff format . && uv run pytest services/review/test_tally.py -q
jj commit -m "review: complete the tie-break ladder with breadth, mean position and first places"
```

---

### Task 4: Wire the ladder into the tally query

**Files:**
- Modify: `services/review/query_interface.py` (add `tie_breaks` to `CompetitionTally`)
- Modify: `services/review/django_impl/query.py` (`get_competition_tally`)
- Test: `services/review/django_impl/test_query.py`

**Interfaces:**
- Consumes: `break_ties`, `TieBreak` from Tasks 2-3.
- Produces: `CompetitionTally.tie_breaks: dict[ProjectId, TieBreak]`, defaulting to an empty dict. `CompetitionTally.tiers` is now post-tiebreak.

- [ ] **Step 1: Write the failing test**

Append to the `TestGetCompetitionTally` class in `services/review/django_impl/test_query.py`:

```python
    def test_separates_projects_the_ordering_rule_left_tied(self, query) -> None:
        # Four ballots leave `first` and `second` on a margin of exactly 0, so
        # Schulze puts them in one tier. Both are ranked by three reviewers, so
        # breadth is level too and the ladder falls through to mean position:
        # `second` averages 4/3 against `first`'s 5/3.
        competition, (first, second, third) = competition_with_projects(3)
        cast_ballot(competition, UserFactory(), [first, second, third])
        cast_ballot(competition, UserFactory(), [second, first, third])
        cast_ballot(competition, UserFactory(), [third, first])
        cast_ballot(competition, UserFactory(), [second])

        tally = query.get_competition_tally(competition.id)

        assert_that(flat_order(tally)[0], equal_to(second.id))
        assert_that(
            tally.tie_breaks[second.id].rung, equal_to("better mean position")
        )
        assert_that(tally.tie_breaks[second.id].tied_with, equal_to((first.id,)))

    def test_reports_no_tie_break_when_the_rule_already_decided(
        self, query
    ) -> None:
        competition, (first, second) = competition_with_projects(2)
        cast_ballot(competition, UserFactory(), [first, second])

        tally = query.get_competition_tally(competition.id)

        assert_that(tally.tie_breaks, equal_to({}))
```

The margin arithmetic, since it is easy to get wrong: ballot 1 gives
`first > second`; ballot 2 gives `second > first`; ballot 3 ranks `first` and
not `second`, so it also gives `first > second`; ballot 4 ranks `second` and not
`first`, giving `second > first`. Net zero. **Do not simplify this to three
ballots** — dropping either of the last two leaves a margin of ±1 and there is
no tie to break, so the test would pass vacuously.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest services/review/django_impl/test_query.py -q -k "tie_break or left_tied"`
Expected: FAIL — `AttributeError: 'CompetitionTally' object has no attribute 'tie_breaks'`

- [ ] **Step 3: Add the field**

In `services/review/query_interface.py`, import `TieBreak` and add the field to `CompetitionTally`:

```python
from services.review.tally import MarginMatrix, ProjectId, ProjectSupport, TieBreak
```

```python
@dataclass(frozen=True)
class CompetitionTally:
    """The computed ordering plus everything needed to distrust it."""

    counted_ballots: int = 0
    projects: dict[ProjectId, Project] = field(default_factory=dict)
    tiers: list[list[ProjectId]] = field(default_factory=list)
    support: dict[ProjectId, ProjectSupport] = field(default_factory=dict)
    margins: MarginMatrix = field(default_factory=dict)
    # Populated only for projects whose rank came from the tie-break ladder.
    tie_breaks: dict[ProjectId, TieBreak] = field(default_factory=dict)
```

- [ ] **Step 4: Call the ladder**

In `services/review/django_impl/query.py`, add `break_ties` to the tally import block, then rewrite the body of `get_competition_tally` after `margins` is computed:

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest services/review/ tests/test_voting_results.py -q`
Expected: PASS.

`test_projects_the_rule_cannot_separate_share_a_rank` in `tests/test_voting_results.py` must still pass — its two projects are level on every rung (each has one 1st place, both ranked by 2 reviewers, both mean 1.5), so the ladder is exhausted and the shared rank stands. If it fails, the ladder is separating something it should not; fix the ladder, not the test.

- [ ] **Step 6: Commit**

```bash
uv run ruff check --fix . && uv run ruff format . && make test
jj commit -m "review: apply the tie-break ladder in get_competition_tally"
```

---

### Task 5: Mark tie-broken ranks on the results page

**Files:**
- Modify: `apps/projects/admin.py` (`_tally_rows`)
- Modify: `templates/admin/projects/competition/voting_results.html:45-64`
- Modify: `docs/superpowers/specs/2026-08-06-ranking-tie-break-design.md` (align the `break_ties` signature)
- Test: `tests/test_voting_results.py`

**Interfaces:**
- Consumes: `CompetitionTally.tie_breaks` from Task 4.
- Produces: each row dict from `_tally_rows` gains `tie_break` (a `TieBreak` or `None`) and `tie_break_with` (comma-joined titles of the projects it was tied with, or `""`).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_voting_results.py`:

```python
def _competition_with_a_broken_tie():
    """Two projects Schulze cannot separate; `b` wins on mean position.

    The last two ballots are what hold the a/b margin at zero — one ranks `a`
    and not `b`, the other the reverse. Drop either and the margin becomes ±1,
    there is no tie, and the test proves nothing.
    """
    a, b, c = ProjectFactory.create_batch(3)
    competition = _make_competition_with_ballots(
        [
            (UserFactory(), [a, b, c]),
            (UserFactory(), [b, a, c]),
            (UserFactory(), [c, a]),
            (UserFactory(), [b]),
        ],
        projects=[a, b, c],
    )
    return competition, a, b


@pytest.mark.django_db
class TestVotingResultsTieBreaks:
    def test_marks_a_rank_that_came_from_a_tie_break(self, admin_client):
        competition, a, b = _competition_with_a_broken_tie()

        response = admin_client.get(_results_url(competition))

        assert_that(
            _row_for(response, b)["tie_break"].rung,
            equal_to("better mean position"),
        )
        assert_that(_row_for(response, b)["tie_break_with"], equal_to(a.title))
        assert_that(_ranks(response)[b.id], equal_to(1))

    def test_names_the_rung_in_the_rendered_page(self, admin_client):
        competition, _a, _b = _competition_with_a_broken_tie()

        content = admin_client.get(_results_url(competition)).content.decode()

        assert_that("better mean position" in content, equal_to(True))

    def test_leaves_untied_rows_unmarked(self, admin_client):
        p1, p2 = ProjectFactory.create_batch(2)
        competition = _make_competition_with_ballots(
            [(UserFactory(), [p1, p2])]
        )

        response = admin_client.get(_results_url(competition))

        assert_that(_row_for(response, p1)["tie_break"], none())

    def test_an_exhausted_ladder_leaves_a_shared_rank_unmarked(self, admin_client):
        p1, p2, p3 = ProjectFactory.create_batch(3)
        competition = _make_competition_with_ballots(
            [
                (UserFactory(), [p1, p2, p3]),
                (UserFactory(), [p2, p1, p3]),
            ]
        )

        response = admin_client.get(_results_url(competition))

        assert_that(_ranks(response)[p1.id], equal_to(1))
        assert_that(_ranks(response)[p2.id], equal_to(1))
        assert_that(_row_for(response, p1)["tie_break"], none())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_voting_results.py -q -k TieBreaks`
Expected: FAIL — `KeyError: 'tie_break'`

- [ ] **Step 3: Expose the tie-break on each row**

In `apps/projects/admin.py`, replace `_tally_rows` with:

```python
def _tally_rows(tally: CompetitionTally) -> list[dict[str, Any]]:
    ranks = _ranks_by_project(tally)
    ordered_ids = [project_id for tier in tally.tiers for project_id in tier]

    return [
        {
            "project": tally.projects[project_id],
            "rank": ranks[project_id],
            "tie_break": tally.tie_breaks.get(project_id),
            "tie_break_with": ", ".join(
                tally.projects[other].title
                for other in tally.tie_breaks[project_id].tied_with
            )
            if project_id in tally.tie_breaks
            else "",
            "first_place_count": tally.support[project_id].first_place_count,
            "ranked_by_count": tally.support[project_id].ranked_by_count,
            "mean_position": tally.support[project_id].mean_position,
            "margins": [
                None if other_id == project_id else tally.margins[project_id][other_id]
                for other_id in ordered_ids
            ],
        }
        for project_id in ordered_ids
    ]
```

- [ ] **Step 4: Mark the rank cell and add the footnote**

In `templates/admin/projects/competition/voting_results.html`, replace the rank `<td>` (currently lines 46-52) with:

```html
        <td style="padding: 8px 12px; text-align: center; font-weight: bold; font-size: 18px;">
          {% if row.rank == 1 %}
            <span style="color: #ca8a04;">{{ row.rank }}</span>
          {% else %}
            {{ row.rank }}
          {% endif %}{% if row.tie_break %}<span style="font-size: 12px; font-weight: normal; opacity: 0.7;" title="Placed by tie-break">&nbsp;*</span>{% endif %}
        </td>
```

Immediately after the results `</table>`, add:

```html
  {% for row in results %}{% if row.tie_break %}
  {% if forloop.first %}<div style="margin-top: 10px;">{% endif %}
    <p style="opacity: 0.7; font-size: 12px; margin: 2px 0;">
      * <strong>{{ row.rank }}. {{ row.project.title }}</strong> — separated from
      {{ row.tie_break_with }} by {{ row.tie_break.rung }}.
    </p>
  {% endif %}{% endfor %}
  </div>
```

Note the `{% if forloop.first %}` opens the wrapper on the first row of the loop, not the first tie-broken row; if no row has a tie-break the wrapper still opens and closes empty, which renders nothing visible. Keep it simple rather than clever.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_voting_results.py -q`
Expected: PASS.

- [ ] **Step 6: Align the spec with the implemented signature**

In `docs/superpowers/specs/2026-08-06-ranking-tie-break-design.md`, change the `break_ties` code block's return annotation from `dict[ProjectId, str]` to `dict[ProjectId, TieBreak]` and note that `TieBreak` carries `rung` and `tied_with`. A spec that disagrees with the code is worse than no spec.

- [ ] **Step 7: Commit**

```bash
uv run ruff check --fix . && uv run ruff format . && uv run pytest tests/test_voting_results.py -q
jj commit -m "admin: mark ranks decided by a tie-break and name the rung"
```

---

### Task 6: Explain the whole method on the page

The prose block from the spec, verbatim. Always visible, below the pairwise grid. Replaces the current one-paragraph note but must keep its "only completed reviews are counted" point.

**Files:**
- Modify: `templates/admin/projects/competition/voting_results.html:68-73` (replace the note) and after the pairwise grid table
- Test: `tests/test_voting_results.py`

**Interfaces:**
- Consumes: nothing. Static copy.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_voting_results.py`:

```python
@pytest.mark.django_db
class TestVotingResultsMethodExplanation:
    def test_explains_the_ranking_and_the_tie_break_sequence(self, admin_client):
        p1, p2 = ProjectFactory.create_batch(2)
        competition = _make_competition_with_ballots(
            [(UserFactory(), [p1, p2])]
        )

        content = admin_client.get(_results_url(competition)).content.decode()

        for phrase in [
            "How this order is worked out",
            "strongest chain",
            "least-bad worst defeat",
            "ranked by more reviewers",
            "better mean position",
            "more first-place votes",
            "Only completed reviews are counted",
        ]:
            assert_that(phrase in content, equal_to(True), phrase)

    def test_shows_the_worked_example_for_the_first_test(self, admin_client):
        p1, p2 = ProjectFactory.create_batch(2)
        competition = _make_competition_with_ballots(
            [(UserFactory(), [p1, p2])]
        )

        content = admin_client.get(_results_url(competition)).content.decode()

        assert_that("A beats B by 2" in content, equal_to(True))
        assert_that("least bad" in content, equal_to(True))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_voting_results.py -q -k MethodExplanation`
Expected: FAIL — `AssertionError` on `"How this order is worked out"`.

- [ ] **Step 3: Replace the short note**

In `templates/admin/projects/competition/voting_results.html`, delete the existing `<p style="opacity: 0.6; font-size: 12px; margin-top: 12px;">Order is computed by the Schulze method…</p>` block and replace it with a one-line pointer:

```html
  <p style="opacity: 0.6; font-size: 12px; margin-top: 12px;">
    Only completed reviews are counted, and a low "ranked by" count means the
    placement rests on few opinions. The method is explained in full below.
  </p>
```

- [ ] **Step 4: Add the explanation after the pairwise grid**

At the end of the `{% else %}` branch — after the pairwise margins `</table>` and before the `{% endif %}` — insert:

```html
  <h3 style="margin-top: 32px;">How this order is worked out</h3>

  <h4 style="margin-bottom: 4px;">Step 1 &mdash; the order before any tie-break</h4>
  <div style="font-size: 13px; max-width: 900px; line-height: 1.5;">
    <p><strong>Every ballot becomes a set of one-to-one comparisons.</strong>
    A project a reviewer ranked counts as preferred over every project they placed
    below it, and over every project they left unranked. Two projects a reviewer
    left unranked count for nothing against each other &mdash; leaving a project out
    says &ldquo;no opinion&rdquo;, not &ldquo;last place&rdquo;.</p>

    <p><strong>Those comparisons are added up per pair.</strong> The margin is the
    number of ballots preferring X over Y minus the number preferring Y over X. A
    margin of +3 means three more reviewers put X above Y than put Y above X. That
    is the grid above.</p>

    <p><strong>Projects are ordered by strongest chain of victories.</strong> X is
    placed above Y when the strongest chain running from X to Y is stronger than the
    strongest chain running back. A chain is only as strong as its weakest link: if
    X beats P by 5 and P beats Y by 2, the chain X &rarr; P &rarr; Y is worth 2.
    Chains matter because head-to-head results can run in a loop, and this resolves
    the loop without ignoring any of it.</p>

    <p><strong>A project's rank is the number of projects it is placed above.</strong>
    If one project is preferred over every other project one-to-one, it always comes
    first. Projects placed above the same number of others share a rank &mdash; that
    is a tie, and the sequence below applies.</p>
  </div>

  <h4 style="margin-bottom: 4px;">Step 2 &mdash; breaking a tie</h4>
  <div style="font-size: 13px; max-width: 900px; line-height: 1.5;">
    <p>Each test below is applied only among the tied projects, in this order. The
    first test that separates them decides the order; the rest are not consulted.</p>

    <p><strong>1. Least-bad worst defeat.</strong> Look only at how the tied projects
    did against each other. Each one's worst defeat is its biggest losing margin
    within that group. The one whose worst defeat is least bad is placed first.</p>

    <div style="margin: 8px 0 8px 16px; padding: 10px 14px; border-left: 3px solid var(--hairline-color); background: rgba(0,0,0,0.02);">
      <p style="margin-top: 0;">Example &mdash; three tied projects whose results run in a loop:</p>
      <p><strong>A beats B by 2 &middot; B beats C by 4 &middot; C beats A by 6</strong></p>
      <table style="border-collapse: collapse; font-size: 13px;">
        <tr><th style="text-align: left; padding: 3px 14px 3px 0;">Project</th><th style="text-align: left; padding: 3px 14px 3px 0;">Worst defeat within the group</th><th></th></tr>
        <tr><td style="padding: 3px 14px 3px 0;">A</td><td style="padding: 3px 14px 3px 0;">&minus;6 (to C)</td><td></td></tr>
        <tr><td style="padding: 3px 14px 3px 0;">B</td><td style="padding: 3px 14px 3px 0;">&minus;2 (to A)</td><td style="color: #ca8a04;">&larr; least bad</td></tr>
        <tr><td style="padding: 3px 14px 3px 0;">C</td><td style="padding: 3px 14px 3px 0;">&minus;4 (to B)</td><td></td></tr>
      </table>
      <p style="margin-bottom: 0;">No project is unbeaten, so no comparison alone can
      settle it. B is placed first because it lost by less than either of the others did.</p>
    </div>

    <p>This test uses the same margins as the ranking itself, so it can never
    contradict the vote &mdash; it only reads more out of it.</p>

    <p><strong>2. Ranked by more reviewers.</strong> How many reviewers ranked the
    project at all. A project ten reviewers formed a view on is placed above one that
    only four did. Only meaningful when reviewers rank some projects and not others.</p>

    <p><strong>3. Better mean position.</strong> The average position the project was
    given, among the reviewers who ranked it. Lower is better &mdash; a mean of 2.1
    beats 3.4. A project nobody ranked has no mean position and is placed last.</p>

    <p><strong>4. More first-place votes.</strong> How many reviewers put the project top.</p>

    <p>Tests 3 and 4 measure <em>how much</em> reviewers preferred a project rather
    than <em>how often</em>, which is the kind of scoring this method deliberately
    moves away from &mdash; a project a few reviewers love and most rank last can
    score well on both. They come last for that reason, and only ever see projects
    the margins could not separate at all.</p>

    <p><strong>If all four tests tie</strong>, the projects are indistinguishable on
    this vote. They keep a shared rank and the choice is yours.</p>
  </div>
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_voting_results.py -q`
Expected: PASS.

- [ ] **Step 6: Look at the page**

Run the dev server (`make dev`) and open the results page for one of the loaded production competitions, e.g. Hvítlaukur, which has two tie-broken ranks. Confirm the `*` markers, the footnotes, and that the explanation reads correctly and is not visually overwhelming.

- [ ] **Step 7: Commit**

```bash
uv run ruff check --fix . && uv run ruff format . && uv run pytest tests/test_voting_results.py -q
jj commit -m "admin: explain the ranking method and tie-break sequence on the results page"
```

---

### Task 7: Lock in the five historical ties as regression fixtures

The ladder was designed against these five tied groups from the production ballot export. They are the cases that must not drift.

**Files:**
- Test: `services/review/test_tally.py`

**Interfaces:**
- Consumes: `break_ties`, `support_for`, `margin_matrix` from Tasks 2-3.
- Produces: nothing.

- [ ] **Step 1: Write the test**

Append to `services/review/test_tally.py`:

```python
class TestHistoricalTies:
    """The five tied groups in the production ballot export, August 2026.

    Signals are the real ones. These are the cases the ladder was designed
    against, so a change in outcome here is a change in policy, not a refactor.
    """

    def test_naepa_rank_two_loop_resolves_to_habitera(self) -> None:
        utsoluvaktin, utsolur, habitera = A, B, C
        margins = margin_matrix(
            {(utsoluvaktin, utsolur): 2, (habitera, utsoluvaktin): 2}
        )
        margins[utsolur][habitera] = 0
        margins[habitera][utsolur] = 0
        support = support_for(
            {
                utsoluvaktin: (1, 8, 3.125),
                utsolur: (2, 8, 2.75),
                habitera: (2, 8, 2.875),
            }
        )

        tiers, reasons = break_ties([[utsoluvaktin, utsolur, habitera]], margins, support)

        assert_that(tiers[0], equal_to([habitera]))
        assert_that(reasons[habitera].rung, equal_to("least-bad worst defeat"))

    def test_hvitlaukur_rank_three_resolves_on_the_head_to_head(self) -> None:
        icelandic_data, kronan = A, B
        margins = margin_matrix({(icelandic_data, kronan): 1})
        support = support_for({icelandic_data: (0, 11, 4.727), kronan: (1, 11, 4.273)})

        tiers, reasons = break_ties([[icelandic_data, kronan]], margins, support)

        assert_that(tiers, equal_to([[icelandic_data], [kronan]]))
        assert_that(reasons[icelandic_data].rung, equal_to("least-bad worst defeat"))

    def test_hvitlaukur_rank_five_does_not_reward_the_polarising_project(
        self,
    ) -> None:
        # chessanalyses had 5 first-place votes -- more than the competition
        # winner -- and still loses, because it lost head to head.
        where_to_park, chessanalyses = A, B
        margins = margin_matrix({(where_to_park, chessanalyses): 1})
        support = support_for(
            {where_to_park: (1, 11, 5.182), chessanalyses: (5, 11, 4.455)}
        )

        tiers, reasons = break_ties([[where_to_park, chessanalyses]], margins, support)

        assert_that(tiers, equal_to([[where_to_park], [chessanalyses]]))
        assert_that(reasons[where_to_park].rung, equal_to("least-bad worst defeat"))

    def test_linsubaunir_rank_two_falls_through_to_mean_position(self) -> None:
        navoa, runur = A, B
        margins = margin_matrix({(navoa, runur): 0})
        support = support_for({navoa: (1, 14, 4.429), runur: (2, 14, 3.929)})

        tiers, reasons = break_ties([[navoa, runur]], margins, support)

        assert_that(tiers, equal_to([[runur], [navoa]]))
        assert_that(reasons[runur].rung, equal_to("better mean position"))

    def test_linsubaunir_rank_four_falls_through_to_mean_position(self) -> None:
        bilaleikir, beadblueprint = A, B
        margins = margin_matrix({(bilaleikir, beadblueprint): 0})
        support = support_for(
            {bilaleikir: (1, 14, 5.714), beadblueprint: (2, 14, 5.214)}
        )

        tiers, reasons = break_ties([[bilaleikir, beadblueprint]], margins, support)

        assert_that(tiers, equal_to([[beadblueprint], [bilaleikir]]))
        assert_that(reasons[beadblueprint].rung, equal_to("better mean position"))
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest services/review/test_tally.py -q -k HistoricalTies`
Expected: PASS (5 passed). These should pass immediately — the ladder was built for them. If any fails, the ladder does not match the design; fix the ladder.

- [ ] **Step 3: Verify against the real data end to end**

Run the analyser over the production export and confirm the five tied groups now resolve as the table in the spec says:

```bash
uv run python scripts/analyse_ballots.py --in /tmp/nglspn-export --only "Hvítlaukur"
```

Expected: no shared ranks at 3 or 5; icelandic-data above kronan-inflation, Where to Park above chessanalyses.

- [ ] **Step 4: Full suite and commit**

```bash
uv run ruff check . && uv run ruff format --check . && make test
jj commit -m "review: pin the five historical tied groups as regression fixtures"
```

---

## Self-Review

**Spec coverage:**

| Spec section | Task |
|---|---|
| Ladder rung 1 (minimax) | 2 |
| Ladder rungs 2-4 + exhaustion | 3 |
| `break_ties` signature and placement outside `OrderingRule` | 2 |
| `_support_signals` / `ProjectSupport` move to `tally.py` | 1 |
| `ProjectSupport` re-exported from `query_interface` | 1, step 5 |
| Page change 1 — mark tie-broken ranks, footnote naming the rung | 5 |
| Page change 2 — full prose explanation, verbatim copy | 6 |
| Page change 3 — keep "only completed reviews are counted" | 6, step 3 + test |
| Worked example is a test fixture | 2, step 1 (`test_a_three_way_loop_is_settled_by_the_least_bad_defeat`) |
| Page rendering tests (marker, exhausted ladder) | 5 |
| Five historical ties as regression fixtures | 7 |
| No migration, no API change, no joint-winner schema | Global constraints |

No gaps.

**Deviation from spec:** `break_ties` returns `dict[ProjectId, TieBreak]` rather than `dict[ProjectId, str]`, because the footnote needs to name the projects the tie was against. Task 5 step 6 updates the spec to match.

**Type consistency:** `ProjectSupport` (Task 1) → consumed by `ScoreRung` and every rung (Tasks 2-3) → `break_ties` (Task 2) → `CompetitionTally.tie_breaks` (Task 4) → `_tally_rows` row key `tie_break` (Task 5) → template `row.tie_break.rung` (Task 5). Rung name strings are identical in `TIE_BREAK_RUNGS` (Task 3), the tests (Tasks 2, 3, 5, 7) and the template copy (Task 6).
