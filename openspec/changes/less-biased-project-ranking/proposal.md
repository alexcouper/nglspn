## Why

Reviewers are handed a pre-ordered list of every project in the competition and told to drag it into shape ([`RankingList.tsx`](../../../src/web-ui/src/app/competitions/[id]/RankingList.tsx)). There is no "unranked" state — submitting means submitting a complete ordering. A reviewer who only cares about two projects moves those to the top and submits, and the remaining six keep their default order, which the tally then counts as a genuine preference.

The default order is `Project.Meta.ordering = ["-created_at"]` and it is **identical for every reviewer**. So the noise is not random noise that cancels across ~15 voters — it is correlated, and it accumulates into what the results table reads as consensus. That is why mid-table projects appear strongly endorsed when nobody actually chose them. See [GitHub issue #70](https://github.com/alexcouper/nglspn/issues/70).

Fixing the UI alone would make things worse. The tally is a Borda count pinned to the total project count (`apps/projects/admin.py:846`), and under truncated ballots every points-based scheme rewards short ballots — the fewer projects you rank, the larger the gap you create between your favourite and everyone else. The ballot and the tally have to change together.

There is no competition in `voting` status right now, so this ships before the next round with no data migration.

## What Changes

**Ballot — reviewers choose what to rank**

- **BREAKING** (UX, not API): the single sortable list of all projects is replaced by a ranked list plus an unranked pool. Projects start unranked; a reviewer adds only the ones they care about.
- Ranked entries keep the existing drag-and-drop and up/down controls, plus a remove action. Added projects append to the bottom of the ranked list.
- Side-by-side on desktop; two tabs on mobile. Adding from the pool does not switch tabs.
- No minimum and no maximum. An empty ballot is a valid abstention, behind a confirmation step.
- The unranked pool is ordered per-reviewer by a deterministic keyed sort on `sha256(user_id:competition_id:project_id)`, so each reviewer sees a stable but different order and browse-position bias stops being correlated across reviewers.

**Tally — pairwise instead of positional**

- Ballots are reduced to a pairwise margin matrix: a ranked project beats every lower-ranked and every unranked project; two unranked projects contribute nothing. Truncating a ballot no longer changes any comparison the reviewer did express.
- The final ordering is computed by the Schulze method (strongest paths) over that matrix. The ranking rule is isolated from the matrix so it can be swapped without touching ballot reduction.
- **BREAKING**: the Borda scoring in `CompetitionAdmin.voting_results_view` is removed. The admin results page shows the Schulze order alongside the raw signals an admin needs — first-place votes, how many reviewers ranked the project at all, mean position among those who did, and the pairwise grid. The page stays advisory; `Competition.winner` is still set by hand.

**Correctness fixes in `update_rankings`**

- Wrap the delete-then-`bulk_create` in `transaction.atomic` — today a failed create leaves the reviewer with no ballot.
- Reject duplicate project IDs with a 400 instead of letting the unique constraint raise a 500 *after* the delete has landed.
- Block ranking updates when the review status is `ENDED`, not just `COMPLETED`.
- Flush the pending 500 ms autosave before submitting, so a reorder immediately followed by Submit is not silently dropped by the `COMPLETED` guard.
- Correct `MyReviewClient.updateRankings`, which is annotated as returning `ReviewCompetitionDetailResponse` while the endpoint returns `SuccessResponse`.

## Capabilities

### New Capabilities

- `project-ranking-ballot`: reviewer-facing partial ballot — ranked list plus unranked pool, add/remove/reorder, empty-ballot abstention, per-reviewer deterministic pool ordering, and the submission validation rules on `PUT /api/my/reviews/competitions/{id}/rankings`.
- `competition-vote-tally`: reduction of ballots to a pairwise margin matrix, Schulze ordering over that matrix, and the admin results view that presents both the computed order and the underlying support signals.

### Modified Capabilities

_(none — no existing spec covers voting or ranking)_

## Impact

- **Django backend**: ranking moves behind the service layer. Ranking is currently the one domain that bypasses it — `api/routers/my_review.py` and `CompetitionAdmin.voting_results_view` both touch `ProjectRanking` directly, and `services/review/` holds only `end_review_period` with no query interface at all. This change adds `ReviewQueryInterface`/`DjangoReviewQuery` (registered as `reviews` on `QueryServices`), a `replace_ballot` handler method, and pure tally functions in `services/review/tally.py`. The router and the admin view become thin; `voting_results.html` is rewritten.
- **Data model**: none. `ProjectRanking` already stores one row per ranked project, so a partial ballot is simply fewer rows. No migration.
- **Web UI**: `RankingList.tsx` split into ranked list and pool, new tab shell in `MyRanking.tsx`, `CompetitionReveal.tsx` initial-ordering logic replaced by the server-supplied pool order.
- **OpenAPI**: the reviewer detail response changes shape (pool ordering) — regenerate `backend-openapi.json` and run `npm run generate-types`, per [CONTRIBUTING.md](../../../CONTRIBUTING.md).
- **Tests**: `tests/test_voting_results.py` currently only builds full permutations and pins Borda — it is rewritten against the new rule. There are **no** frontend tests for any ranking component today; the unused `data-testid="ranked-card"` and `data-testid="rank-badge"` hooks in `RankingList.tsx` get their first use.
- **Existing data**: closed competitions hold genuine full-permutation ballots, which the pairwise reduction handles unchanged. No competition is in `voting` status, so nothing needs resetting.
