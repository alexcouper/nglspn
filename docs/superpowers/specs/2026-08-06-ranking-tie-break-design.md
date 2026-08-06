# Breaking Ties in the Competition Tally

## Problem

The Schulze ordering in [`services/review/tally.py`](../../../src/django-backend/services/review/tally.py)
returns *tiers* — a list of lists — because two projects the method cannot
separate share a rank. Nothing decides what happens next, so the admin results
page renders `3 =` twice and leaves the admin to interpret it.

That is tolerable at rank 3. At rank 1 it is not: `Competition.winner` is a
single ForeignKey and someone has to be given the prize.

Ties are not hypothetical. Across the eight production competitions replayed
from the ballot export, five tied groups occurred in three competitions:

| competition | ballots | tied at | direct head-to-head |
|---|---|---|---|
| Hvítlaukur | 11 | rank 3 | icelandic-data beats kronan-inflation **+1** |
| Hvítlaukur | 11 | rank 5 | Where to Park beats chessanalyses **+1** |
| Næpa | 8 | rank 2 (3-way) | **cyclic** — Útsöluvaktin > utsolur, habitera > Útsöluvaktin, utsolur = habitera |
| Linsubaunir | 14 | rank 2 | Navoa vs runur.is **+0** |
| Linsubaunir | 14 | rank 4 | bilaleikir vs beadblueprint **+0** |

No tie has yet landed at rank 1, but Chili was decided by a margin of +1 out of
15 ballots, so it is a matter of time.

The tied groups are three different problems wearing the same label:

- **Path-equal but directly decisive** (Hvítlaukur). Schulze's strongest paths
  are equal in both directions, yet one project beat the other head to head.
- **Cyclic** (Næpa). A beats B, B beats C, C ties A. No comparison can rank them.
- **Dead level** (Linsubaunir). Margin exactly 0, no path either way. Genuinely
  indistinguishable.

Any rule has to cope with all three.

## Goals

- A tie at any rank resolves to a definite order wherever the ballots contain
  grounds to do so.
- The grounds are visible on the results page. A rank produced by a tiebreak
  must not look like a rank produced by the vote.
- The rule is fixed and published *before* voting opens. A tiebreaker chosen
  after the tie is visible is not defensible.
- Each rung is independently testable without a database.

## Non-goals

- **No joint-winner schema.** The ladder below resolved all five historical
  ties, so `winner` stays a single ForeignKey. "Joint" means the tier stands on
  the page and the admin picks one by hand — not a data structure. Revisit if
  the ladder is ever actually exhausted, not before.
- **No change to the Schulze ordering itself.** Tiebreaking is a stage applied
  to its output.
- **No automatic winner selection.** `Competition.winner` is still set by hand,
  and setting it still closes the competition.

## Design

### The ladder

A tie is resolved by applying rungs in order, each filtering the survivors of
the last. Only projects within one tier are ever compared.

| # | rung | signal | resolves |
|---|---|---|---|
| 1 | `minimax` | least-bad worst defeat *within the tied set* (highest wins) | path-equal and cyclic ties |
| 2 | `breadth` | ranked by more reviewers (highest wins) | thin-support ties (partial ballots only) |
| 3 | `mean position` | mean position among reviewers who ranked it (**lowest** wins — position 1 is best) | dead-level ties |
| 4 | `first places` | 1st-place votes (highest wins) | dead-level ties rung 3 misses |
| 5 | — | still tied → the tier stands | genuinely identical |

A project with no rankers has no mean position; it sorts last on rung 3.

**Minimax leads deliberately.** It consumes the same margin matrix as the
ordering rule it is correcting, so it never introduces a claim the pairwise
result contradicts. For a two-way tie, "worst defeat within the set" *is* the
head-to-head result; unlike head-to-head it also resolves cycles.
[`design.md` for `less-biased-project-ranking`](../../../openspec/changes/less-biased-project-ranking/design.md)
already names minimax as the documented alternative over the same matrix, so it
adds no new concept.

**Rungs 3 and 4 are positional and must stay last.** Mean position and
first-place counts measure *how much* better, which is the Borda logic the
pairwise tally exists to avoid. On the historical data they disagree with the
head-to-head result in both cases where one exists:

| tied group | minimax | most 1sts |
|---|---|---|
| Hvítlaukur r3 | icelandic-data | kronan-inflation — **opposite** |
| Hvítlaukur r5 | Where to Park | chessanalyses.com — **opposite** |

chessanalyses.com is the reason. It has five 1st-place votes — more than
Hvítlaukur's winner husro.is, which has four — and finishes 5th because most
reviewers put it near the bottom. Promoting it on 1st-place count would
reintroduce exactly the plurality bias the change removed. Below minimax the
rung is harmless: it only ever sees projects the margins could not separate.

### What the ladder does to the historical ties

| tied group | resolved by | outcome |
|---|---|---|
| Hvítlaukur r3 | minimax | icelandic-data |
| Hvítlaukur r5 | minimax | Where to Park |
| Næpa r2 | minimax | habitera.is |
| Linsubaunir r2 | mean position | runur.is |
| Linsubaunir r4 | mean position | beadblueprint.uk |

All five resolve. The `breadth` and `first places` rungs never fire — breadth
because every historical ballot was full, so ranked-by is always equal. It
earns its place going forward, when partial ballots make it meaningful.

### Where it lives

`break_ties` is a separate stage, not part of `OrderingRule`. The protocol is
`(margins) -> tiers`; the ladder additionally needs support signals, so folding
it in would widen a deliberately narrow interface.

```python
def break_ties(
    tiers: list[list[ProjectId]],
    margins: MarginMatrix,
    support: dict[ProjectId, ProjectSupport],
) -> tuple[list[list[ProjectId]], dict[ProjectId, str]]:
    """Split tied tiers as far as the ladder allows.

    Returns the new tiers and, for each project whose placement came from a
    tiebreak, the name of the rung that decided it.
    """
```

`DjangoReviewQuery.get_competition_tally` calls the ordering rule, then
`break_ties`, and puts the rung names on `CompetitionTally` alongside the tiers.

### A refactor it requires

`_support_signals` currently sits in
[`services/review/django_impl/query.py`](../../../src/django-backend/services/review/django_impl/query.py)
but is already ORM-free, and `ProjectSupport` is declared in `query_interface.py`.
Both move into `tally.py`:

- the ladder needs both, and keeping it pure is what makes exhaustive tests cheap
  — the same argument the existing design gives for the tally;
- `query_interface.py` already imports `MarginMatrix` and `ProjectId` from
  `tally`, so the dependency runs the right way already.

`ProjectSupport` is re-exported from `query_interface` so existing importers do
not change.

### The results page

Three changes to `templates/admin/projects/competition/voting_results.html`.

**1. Mark ranks the ladder produced.**

- the rank cell reads `3 *` where the placement came from a tiebreak;
- a footnote under the table names the rung per affected project, e.g.
  *"3 — separated from kronan-inflation by least-bad worst defeat"*;
- if the ladder is exhausted, the affected rows keep a shared rank and the page
  states plainly that the projects are indistinguishable and the choice is the
  admin's.

The marker matters more than it looks. The page currently renders a rank-1 won
by +1 identically to one won by +15; adding a decisive tiebreak without saying
so would compound that.

**2. Explain the method in full, in prose, below the pairwise grid.**

Always visible, not collapsed — an admin defending a result to an entrant needs
to be able to read it and repeat it. Replaces the current one-paragraph note.
The copy, verbatim:

> ## How this order is worked out
>
> ### Step 1 — the order before any tiebreak
>
> **Every ballot becomes a set of one-to-one comparisons.** A project a reviewer
> ranked counts as preferred over every project they placed below it, and over
> every project they left unranked. Two projects a reviewer left unranked count
> for nothing against each other — leaving a project out says "no opinion", not
> "last place".
>
> **Those comparisons are added up per pair.** The margin is the number of
> ballots preferring X over Y minus the number preferring Y over X. A margin of
> +3 means three more reviewers put X above Y than put Y above X. That is the
> grid above.
>
> **Projects are ordered by strongest chain of victories.** X is placed above Y
> when the strongest chain running from X to Y is stronger than the strongest
> chain running back. A chain is only as strong as its weakest link: if X beats
> P by 5 and P beats Y by 2, the chain X → P → Y is worth 2. Chains matter
> because head-to-head results can run in a loop, and this resolves the loop
> without ignoring any of it.
>
> **A project's rank is the number of projects it is placed above.** If one
> project is preferred over every other project one-to-one, it always comes
> first. Projects placed above the same number of others share a rank — that is
> a tie, and the sequence below applies.
>
> ### Step 2 — breaking a tie
>
> Each test below is applied only among the tied projects, in this order. The
> first test that separates them decides the order; the rest are not consulted.
>
> **1. Least-bad worst defeat.** Look only at how the tied projects did against
> each other. Each one's worst defeat is its biggest losing margin within that
> group. The one whose worst defeat is least bad is placed first.
>
> Example — three tied projects whose results run in a loop:
>
> > A beats B by 2 · B beats C by 4 · C beats A by 6
> >
> > | project | worst defeat within the group | |
> > |---|---|---|
> > | A | −6 (to C) | |
> > | B | −2 (to A) | ← least bad |
> > | C | −4 (to B) | |
> >
> > No project is unbeaten, so no comparison alone can settle it. B is placed
> > first because it lost by less than either of the others did.
>
> This test uses the same margins as the ranking itself, so it can never
> contradict the vote — it only reads more out of it.
>
> **2. Ranked by more reviewers.** How many reviewers ranked the project at all.
> A project ten reviewers formed a view on is placed above one that only four
> did. Only meaningful when reviewers rank some projects and not others.
>
> **3. Better mean position.** The average position the project was given, among
> the reviewers who ranked it. Lower is better — a mean of 2.1 beats 3.4. A
> project nobody ranked has no mean position and is placed last.
>
> **4. More first-place votes.** How many reviewers put the project top.
>
> Tests 3 and 4 measure *how much* reviewers preferred a project rather than
> *how often*, which is the kind of scoring this method deliberately moves away
> from — a project a few reviewers love and most rank last can score well on
> both. They come last for that reason, and only ever see projects the margins
> could not separate at all.
>
> **If all four tests tie**, the projects are indistinguishable on this vote.
> They keep a shared rank and the choice is yours.

**3. Keep the "only completed reviews are counted" note**, which the current
paragraph carries and the new copy must not lose.

## Testing

Pure, no database, in `services/review/test_tally.py`:

- each rung in isolation, on a hand-built matrix where only that rung can decide;
- rung order — a case where minimax and 1st-places disagree resolves the
  minimax way;
- a cycle resolves by minimax (the Næpa shape);
- a dead-level pair falls through to mean position;
- an exhausted ladder returns a shared tier and no rung name;
- the returned rung names match the rung that actually fired.

Regression fixtures from the production export: the five tied groups above, each
asserting the outcome in the table. These are the cases the rule was designed
against, so they are the ones that must not drift.

`DjangoReviewQuery.get_competition_tally` gets one test that the tiers it
returns are the broken ones, not the raw ordering-rule output.

**The worked example on the page is a test fixture.** The A/B/C loop in the copy
(A beats B by 2, B beats C by 4, C beats A by 6 → B placed first) is asserted
against `break_ties` directly. Explanatory copy that drifts from behaviour is
worse than no copy, and this is the one paragraph an admin will quote back to an
entrant.

The page itself gets a rendering test in `tests/test_voting_results.py`: a
competition whose top tier was split by a tiebreak renders the `*` marker and
names the rung, and one whose ladder is exhausted renders a shared rank without
a marker.

## Rollout

The ladder changes only the advisory results page. No migration, no API change —
no endpoint exposes the tally.

The rule must be in the published competition rules before the next round opens.
Announcing it after a tie is visible makes it look chosen to suit the outcome,
which is the one failure mode no amount of correctness fixes.

## Open questions

- **Should the page flag near-ties as well as broken ties?** A rank-1 margin of
  +1 out of 15 is not a tie but is not a result either, and the page renders it
  identically to +15. Related but separable; raised in review of Chili.
- **Copy language.** The results page is admin-only and English; the published
  rules reviewers read are Icelandic. The rung names need Icelandic equivalents
  if the rules describe them.
