## Context

Reviewers rank projects in a competition. A ballot is the set of `ProjectRanking` rows for one `(reviewer, competition)` — one row per project, with a 1-based `position` ([`apps/projects/models.py:419`](../../../src/django-backend/apps/projects/models.py)). The model already permits a partial ballot; nothing about it needs to change.

What forces full ballots is the UI. [`RankingList.tsx`](../../../src/web-ui/src/app/competitions/[id]/RankingList.tsx) renders every project in a single dnd-kit sortable list where position *is* list index, and [`MyRanking.tsx:139-158`](../../../src/web-ui/src/app/competitions/[id]/MyRanking.tsx) PUTs the whole list on a 500 ms debounce. There is no representation of "I have no opinion about this project". The starting order comes from `Project.Meta.ordering = ["-created_at"]` and is the same for every reviewer.

The tally is a Borda count inlined in `CompetitionAdmin.voting_results_view` ([`apps/projects/admin.py:814-884`](../../../src/django-backend/apps/projects/admin.py)), scoring `total_projects - position + 1`. It is staff-only and advisory — an admin still sets `Competition.winner` by hand, which flips the competition to `closed` via `Competition.save()`.

Scale: roughly 8 projects and 15 reviewers per competition. No competition is currently in `voting` status.

See [proposal.md](proposal.md) for motivation and [GitHub issue #70](https://github.com/alexcouper/nglspn/issues/70).

## Goals / Non-Goals

**Goals:**

- A reviewer expresses preferences only about projects they actually chose to rank.
- A reviewer who ranks fewer projects is neither rewarded nor punished for it.
- Browse-position bias stops being correlated across reviewers.
- The admin results page makes thin support visible rather than hiding it behind a score.
- Ballot reduction and the ordering rule are separable and independently testable.

**Non-Goals:**

- Strategy-proofness. 15 friendly reviewers are not an adversarial electorate; the target is accidental noise, not manipulation.
- Automating winner selection. The tally stays advisory.
- Public-facing results. No API exposes scores today and none is added.
- Changing the data model. No migration.
- Ranking with explicit ties (`A and B are equal, both above C`). Unranked projects are mutually tied, which covers the case that matters.

## Decisions

### Pairwise counting instead of any positional score

**Decision:** reduce each ballot to pairwise preferences rather than assigning points per position.

Once ballots can be truncated, every points-based scheme creates an incentive to truncate, because the points a project receives depend on how many other projects the reviewer bothered to rank. With 8 projects on a 8..1 ladder, take a reviewer who honestly prefers A > B > rest:

| Scheme | Ballot `[A,B]` | Ballot `[A]` | A−B gap |
|---|---|---|---|
| Unranked = 0 | A=8, B=7 | A=8, B=0 | 1 → 8 |
| Unranked = 1 | A=8, B=7, rest=1 | A=8, rest=1 | 1 → 7 |
| Unranked = average of remaining | A=8, B=7, rest=3.5 | A=8, rest=4 | 1 → 4 |

Dropping B from the ballot always increases the push for A over B. There is no constant that fixes it: for the gap to be unaffected you would have to score every unranked project as if it were the reviewer's second choice.

Positional scoring also forces a false claim. Ranking B second *asserts* "A beats B by exactly one step", so a reviewer who thinks A is far better than B is penalised for ranking B at all — the same disease as the default ordering, at the other end of the list.

Pairwise counting has neither problem. `[A]`, `[A,B]` and `[A,B,C,D]` all contribute exactly one "A over B". Truncating removes comparisons; it never inflates one.

**Alternatives considered:** Borda with unranked scored at zero (status quo — worst case in the table above); Borda with the leftover points averaged across unranked projects (equalises each ballot's total influence at 36, but still rewards truncation and still forces the false one-step claim).

### Schulze rather than Copeland or minimax

**Decision:** order projects by the Schulze method over the pairwise matrix.

Copeland — count head-to-head wins — is the easiest to explain but useless at this size. With 8 projects every score lands in `{0..7}`, so a collision-free table requires the scores to be exactly `7,6,5,4,3,2,1,0`, which happens only when the pairwise results already form a perfect total order. Any single cycle collapses two buckets and forces a tie. Copeland produces a clean ordering only in the cases where no tally rule was needed.

Minimax — rank by your worst defeat — discriminates far better, because it measures margins rather than counting wins. Its weakness is that it can elect a project outside the Smith set: by looking only at a single worst defeat it can promote someone who loses to everyone in the top group. That is exactly the kind of result that would make an admin distrust the whole table.

Schulze always elects from the Smith set, always elects a Condorcet winner when one exists, and resolves cycles using indirect chains of defeat. Ties are rare at 15 voters. The cost over minimax is a Floyd–Warshall triple loop — 512 iterations at 8 projects.

**Alternatives considered:** Copeland (rejected, ties); minimax (viable fallback, kept as a documented option since it consumes the same matrix); Ranked Pairs (comparable quality to Schulze, marginally easier to explain, fiddlier cycle-detection loop).

**Accepted limitation:** Schulze does not satisfy later-no-harm. In constructed cases, adding a third choice can hurt your first. The effect is nothing like Borda's and does not matter at this scale, but it should not be described to anyone as truncation-proof.

### Margins rather than winning votes

**Decision:** each matrix cell holds the margin — ballots preferring A over B, minus ballots preferring B over A.

The two diverge exactly when many reviewers ranked neither project. If 3 prefer A, 1 prefers B and 11 ranked neither, margins report "A beats B by 2" while winning votes report "A scores 3". Margins treat a comparison nobody engaged with as a weak result, which is the signal this change exists to surface. Winning votes has better strategy resistance under truncation, which is a non-goal.

The `ranked by N/15` column in the results view exists so an admin can see when an ordering rests on three opinions.

### Deterministic keyed sort for the unranked pool

**Decision:** order the pool by `sha256(f"{user_id}:{competition_id}:{project_id}")`, computed server-side in `GET /api/my/reviews/competitions/{id}`.

Removing the shared default order from the ballot does not remove it from the pool: whatever order the pool is in, the top gets picked more. Per-reviewer ordering does not remove that bias — each reviewer is still nudged by their own list — but it decorrelates it. A bias every reviewer shares aggregates into apparent consensus; a bias pointing in fifteen directions is noise that averages out.

A keyed sort is preferred over `random.Random(seed).shuffle(...)` because it depends on no library internals staying stable across Python versions, and it is trivially testable. Server-side rather than client-side so the order survives across devices and there is one place to test it.

**Alternatives considered:** shuffle per request (rejected — the list would reorder under the reviewer mid-decision, and the component refetches after every autosave); shuffle per client session (rejected — inconsistent across devices, lost on reload); a stored per-reviewer seed column (rejected — a migration for something derivable).

### Ranking moves behind the service layer

**Decision:** ballot reads, ballot writes and the tally all go through `services/review/`. No router or admin view touches `ProjectRanking` directly.

Ranking is currently the one domain in the backend that bypasses the service layer. Every other domain routes through `HANDLERS`/`REPO` ([`services/__init__.py`](../../../src/django-backend/services/__init__.py)), but `api/routers/my_review.py` queries and writes `ProjectRanking` inline, and the tally sits inside `CompetitionAdmin.voting_results_view`. `services/review/` exists but holds a single method, `end_review_period`, and has no query interface at all — `reviews` appears in `HandlerServices` but not in `QueryServices`.

```
  admin view ──┐
  API router ──┼──▶ REPO.reviews / HANDLERS.reviews ──▶ ORM
  (both thin)  │              │
               │              └── calls ──▶ services/review/tally.py  (pure)
```

This change already rewrites the guts of `update_rankings` for atomicity, duplicate rejection and the `ENDED` guard, and replaces the tally wholesale. Moving both behind the service while they are open costs little; doing the reads and leaving the writes inline would leave ranking as the one domain where half the operations are layered and half are not, which is the kind of half-migration that never gets finished.

Requires a new `ReviewQueryInterface` + `DjangoReviewQuery` registered as `reviews` on `QueryServices`, and new methods on the existing `ReviewHandlerInterface`.

### Tally computation stays pure, inside the service package

**Decision:** ballot reduction and the ordering rule live in `services/review/tally.py` as pure functions over plain data — a list of ballots as ordered project-ID sequences, plus the eligible project IDs, in; margins and ranked tiers out. `DjangoReviewQuery` does the ORM work and calls them.

The `handler_interface` + `django_impl` pattern exists for operations with side effects and ORM access. The tally has neither; it is a deterministic function of its inputs, and keeping it ORM-free is what makes its tests fast and exhaustive — which matters because the entire correctness argument for this change lives in those functions.

Placing it inside `services/review/` rather than under `apps/projects/` keeps review-domain logic together and means no caller reaches past `REPO` into a bare module. The purity is about testability, not about escaping the layer.

### The ordering rule is a callable `Protocol`

**Decision:** define the ordering rule as a `typing.Protocol` over `(margins) -> ranked tiers`, with `schulze_order` as the first conforming implementation. The service depends on the protocol, not on `schulze_order` directly.

```python
class OrderingRule(Protocol):
    def __call__(self, margins: MarginMatrix) -> list[list[ProjectId]]: ...
```

Returning *tiers* — a list of lists — rather than a flat ordering keeps ties a first-class result rather than something each rule signals differently. Copeland ties constantly, Schulze rarely; the consumer should not have to know which rule it is talking to in order to render a shared rank.

This is the first `Protocol` in the backend; the established pattern is `ABC` + `@abstractmethod` in `services/*/handler_interface.py` ([`services/registration/handler_interface.py`](../../../src/django-backend/services/registration/handler_interface.py)). The deviation is deliberate and narrow. Those interfaces describe stateful multi-method handlers that are instantiated and registered on `HANDLERS`; structural typing over a single pure function avoids wrapping a function in a class purely to satisfy nominal typing, and needs no registration. The service boundary is still an `ABC` in the house style — the `Protocol` sits strictly below it, inside `tally.py`.

**Alternatives considered:** a plain function reference with no declared interface (rejected — nothing states the contract, and the separability requirement becomes unenforceable); an `ABC` matching house style (rejected — forces a class wrapper and an instantiation ceremony around one function); a registry keyed by rule name (rejected — configurability nobody has asked for; changing the rule is a spec change, not a setting).

### Add/remove buttons rather than cross-container drag

**Decision:** move projects between pool and ranked list with explicit `+ Rank` and `✕` controls. Keep dnd-kit for reordering *within* the ranked list only.

dnd-kit supports multi-container sortables, but dragging across two containers is poor on narrow screens where the containers are separate tabs, and it makes the "I am deliberately choosing this project" action less explicit — which is the entire point of the change. Explicit controls also work with keyboard and touch without extra sensor configuration, and keep the existing `RankingList` reorder logic untouched.

## Risks / Trade-offs

- **Schulze is opaque to an admin who just wants to know who won** → the results view shows the pairwise grid, first-place counts, ranked-by counts and mean position next to the computed order. The order is a recommendation among several signals, not a verdict.
- **Historical competitions will show different results than they did before** → closed competitions hold genuine full permutations, which pairwise reduction handles correctly, and `Competition.winner` is a stored FK that no recomputation touches. Only the advisory table changes.
- **Reviewers accustomed to the old UI may not realise they must now opt in, and submit empty ballots by accident** → empty submission is gated behind a confirmation that states plainly that no projects will be ranked.
- **A pairwise comparison resting on very few opinions can drive the ordering** → surfaced by the `ranked by N/15` column rather than suppressed; an admin can discount it.
- **Cycles could produce an ordering that is hard to justify publicly** → Schulze's result is always from the Smith set, and the pairwise grid is shown so the cycle is visible rather than hidden. Minimax remains a drop-in alternative over the same matrix.
- **Rewriting `voting_results.html` and the tests loses the pinned Borda behaviour** → intended. The existing tests in `tests/test_voting_results.py` only build full permutations and encode the rule being removed.
- **No frontend tests exist for any ranking component** → this change adds them; the unused `data-testid="ranked-card"` and `data-testid="rank-badge"` hooks already in `RankingList.tsx` are the starting point.

## Migration Plan

No data migration. `ProjectRanking` is unchanged, and a partial ballot is simply fewer rows.

1. Ship backend and frontend together — the reviewer detail response changes shape, so regenerate `backend-openapi.json` and run `npm run generate-types` (see [CONTRIBUTING.md](../../../CONTRIBUTING.md)).
2. Ship before the next competition enters `voting` status. Nothing is in `voting` now, so no reviewer is mid-ballot.
3. Existing ballots on closed competitions are left in place.

**Rollback:** revert the deploy. Stored ballots remain valid under the old code — an old full-permutation ballot and a new partial ballot are the same shape, and the old Borda view will simply score unranked projects at zero.

## Open Questions

- **Copy language.** The ranking UI is currently English (`MyRanking.tsx:217`) while parts of the app are Icelandic. New strings follow the surrounding component unless decided otherwise.
- **Should a competition with no Condorcet winner be flagged in the results view?** Cheap to detect and arguably useful context for an admin, but adds a concept to the page.
- **Does the results view need an export?** Out of scope as proposed; worth knowing if an admin currently copies numbers out by hand.
