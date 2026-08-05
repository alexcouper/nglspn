"""Tests for the pure tally functions. No database, no ORM, no fixtures."""

from uuid import NAMESPACE_OID, UUID, uuid5

from hamcrest import assert_that, equal_to

from services.review.tally import (
    MarginMatrix,
    ProjectId,
    reduce_ballots_to_margins,
    schulze_order,
)


def project_id(name: str) -> ProjectId:
    """A readable, stable project id so failures name the project."""
    return uuid5(NAMESPACE_OID, name)


A = project_id("A")
B = project_id("B")
C = project_id("C")
D = project_id("D")
ALL_FOUR = [A, B, C, D]


def margin_matrix(margins: dict[tuple[ProjectId, ProjectId], int]) -> MarginMatrix:
    """Build a complete matrix from the winning side of each pair."""
    projects = list(dict.fromkeys(p for pair in margins for p in pair))
    matrix: MarginMatrix = {a: dict.fromkeys(projects, 0) for a in projects}
    for (winner, loser), value in margins.items():
        matrix[winner][loser] = value
        matrix[loser][winner] = -value
    return matrix


def assert_margin(
    matrix: MarginMatrix, winner: UUID, loser: UUID, expected: int
) -> None:
    assert_that(matrix[winner][loser], equal_to(expected))
    assert_that(matrix[loser][winner], equal_to(-expected))


class TestBallotReduction:
    def test_full_ballot_contributes_every_pairwise_preference(self) -> None:
        margins = reduce_ballots_to_margins([[A, B, C]], [A, B, C])

        assert_margin(margins, A, B, 1)
        assert_margin(margins, A, C, 1)
        assert_margin(margins, B, C, 1)

    def test_ranked_projects_beat_unranked_projects(self) -> None:
        margins = reduce_ballots_to_margins([[C, A]], ALL_FOUR)

        assert_margin(margins, C, A, 1)
        assert_margin(margins, C, B, 1)
        assert_margin(margins, C, D, 1)
        assert_margin(margins, A, B, 1)
        assert_margin(margins, A, D, 1)

    def test_two_unranked_projects_contribute_nothing(self) -> None:
        margins = reduce_ballots_to_margins([[C, A]], ALL_FOUR)

        assert_margin(margins, B, D, 0)

    def test_empty_ballot_contributes_no_preferences(self) -> None:
        margins = reduce_ballots_to_margins([[]], ALL_FOUR)

        for winner in ALL_FOUR:
            for loser in ALL_FOUR:
                assert_that(margins[winner][loser], equal_to(0))

    def test_single_ranked_project_beats_every_other(self) -> None:
        margins = reduce_ballots_to_margins([[A]], ALL_FOUR)

        assert_margin(margins, A, B, 1)
        assert_margin(margins, A, C, 1)
        assert_margin(margins, A, D, 1)
        assert_margin(margins, B, C, 0)
        assert_margin(margins, B, D, 0)
        assert_margin(margins, C, D, 0)

    def test_opposing_ballots_cancel_to_a_margin(self) -> None:
        for_a = [[A, B]] * 9
        for_b = [[B, A]] * 3

        margins = reduce_ballots_to_margins([*for_a, *for_b], [A, B])

        assert_margin(margins, A, B, 6)

    def test_matrix_covers_every_eligible_pair_without_any_ballots(self) -> None:
        margins = reduce_ballots_to_margins([], ALL_FOUR)

        assert_that(sorted(margins, key=str), equal_to(sorted(ALL_FOUR, key=str)))
        for row in margins.values():
            assert_that(sorted(row, key=str), equal_to(sorted(ALL_FOUR, key=str)))

    def test_ineligible_project_is_dropped_from_the_matrix(self) -> None:
        rejected = project_id("rejected")

        margins = reduce_ballots_to_margins([[A, rejected, B]], [A, B])

        assert_that(rejected in margins, equal_to(False))
        assert_that(rejected in margins[A], equal_to(False))
        assert_margin(margins, A, B, 1)


class TestTruncationNeutrality:
    def test_truncated_and_full_ballots_agree_on_ranked_pairs(self) -> None:
        truncated = reduce_ballots_to_margins([[A, B]], ALL_FOUR)
        full = reduce_ballots_to_margins([[A, B, C, D]], ALL_FOUR)

        assert_that(truncated[A][B], equal_to(full[A][B]))

    def test_truncation_only_removes_comparisons_it_never_inflates_one(self) -> None:
        eight = [project_id(name) for name in "ABCDEFGH"]
        first, *rest = eight

        margins = reduce_ballots_to_margins([[first]], eight)

        for other in rest:
            assert_margin(margins, first, other, 1)
        for i, one in enumerate(rest):
            for other in rest[i + 1 :]:
                assert_margin(margins, one, other, 0)


class TestSchulzeOrder:
    def test_condorcet_winner_is_ranked_first(self) -> None:
        margins = margin_matrix({(A, B): 3, (A, C): 5, (B, C): 1})

        assert_that(schulze_order(margins)[0], equal_to([A]))

    def test_cycle_is_resolved_by_strongest_paths(self) -> None:
        margins = margin_matrix({(A, B): 8, (B, C): 6, (C, A): 4})

        assert_that(schulze_order(margins), equal_to([[A], [B], [C]]))

    def test_projects_with_equal_strongest_paths_share_a_tier(self) -> None:
        margins = margin_matrix({(A, B): 0, (A, C): 4, (B, C): 4})

        assert_that(schulze_order(margins), equal_to([[A, B], [C]]))

    def test_ordering_needs_only_a_hand_built_matrix(self) -> None:
        margins = margin_matrix({(A, B): 1})

        assert_that(schulze_order(margins), equal_to([[A], [B]]))

    def test_matrix_with_no_preferences_is_one_tier(self) -> None:
        margins = reduce_ballots_to_margins([], [A, B, C])

        assert_that(schulze_order(margins), equal_to([[A, B, C]]))

    def test_empty_matrix_orders_nothing(self) -> None:
        assert_that(schulze_order({}), equal_to([]))

    def test_ineligible_project_is_absent_from_the_ordering(self) -> None:
        rejected = project_id("rejected")

        margins = reduce_ballots_to_margins([[rejected, A, B]], [A, B])

        assert_that(schulze_order(margins), equal_to([[A], [B]]))
