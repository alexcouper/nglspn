"""Tests for the pure tally functions. No database, no ORM, no fixtures."""

from uuid import NAMESPACE_OID, UUID, uuid5

from hamcrest import assert_that, equal_to

from services.review.tally import (
    MarginMatrix,
    ProjectId,
    ProjectSupport,
    break_ties,
    reduce_ballots_to_margins,
    schulze_order,
    support_signals,
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


def no_support(project_ids: list[ProjectId]) -> dict[ProjectId, ProjectSupport]:
    """Support signals that separate nothing, so only the margins decide."""
    return {p: ProjectSupport(0, 0, None) for p in project_ids}


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

        tiers, reasons = break_ties(
            [[utsoluvaktin, utsolur, habitera]], margins, support
        )

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
