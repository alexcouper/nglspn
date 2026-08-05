Implementation order: the pure tally module first (it carries the correctness argument and needs no ORM), then the admin view that consumes it, then the API changes, then the frontend. Backend and frontend must ship together — see [design.md](design.md) Migration Plan.

## 1. Tally core — pure module

Pure functions over plain data, no ORM. Spec: [`specs/competition-vote-tally/spec.md`](specs/competition-vote-tally/spec.md).

- [ ] 1.1 Write failing tests for ballot reduction in `src/django-backend/apps/projects/test_tally.py`: full ballot, partial ballot, empty ballot, unranked pairs contribute nothing
- [ ] 1.2 Write a failing test asserting truncation neutrality — `[A,B]` and `[A,B,C,D]` contribute an identical A-over-B count
- [ ] 1.3 Implement `reduce_ballots_to_margins(ballots, eligible_project_ids)` in `src/django-backend/apps/projects/tally.py` returning a pairwise margin matrix
- [ ] 1.4 Define the `OrderingRule` `Protocol` — `(margins) -> list[list[ProjectId]]`, ranked tiers so ties are a first-class result — plus the `MarginMatrix` and `ProjectId` type aliases
- [ ] 1.5 Write failing tests for the ordering rule: Condorcet winner first, the 3-cycle from design.md resolves to A/B/C, equal strongest paths land in the same tier
- [ ] 1.6 Implement `schulze_order(margins)` conforming to `OrderingRule`, using the Floyd–Warshall strongest-path computation
- [ ] 1.7 Add a test asserting an ordering rule can be exercised on a hand-built matrix with no ballots, reviewers or competitions in sight
- [ ] 1.8 Add a test asserting ballot reduction produces a complete matrix without invoking any ordering rule
- [ ] 1.9 Add a test asserting ineligible project IDs referenced by a ballot are dropped from both the matrix and the ordering
- [ ] 1.10 Verify `make lint` and `make test` pass from `src/django-backend/`

## 2. Admin results view

- [ ] 2.1 Rewrite `tests/test_voting_results.py` against the new rule — delete the Borda assertions, keep the staff-only and no-completed-voters cases, add partial-ballot cases
- [ ] 2.2 Add a test asserting the view reports ranked-by counts (e.g. 2 of 15) for a thinly-supported project
- [ ] 2.3 Replace the Borda loop in `CompetitionAdmin.voting_results_view` (`apps/projects/admin.py:814-884`) with a query that collects completed reviewers' ballots and delegates to `tally.py`, typed against `OrderingRule` rather than `schulze_order` directly
- [ ] 2.4 Build the view context: rank (flattening tiers so a shared tier shares a rank), first-place count, ranked-by count, mean position among rankers, and the pairwise margin grid
- [ ] 2.5 Rewrite `templates/admin/projects/competition/voting_results.html` — replace the 1st..Nth position histogram and the prose describing Borda scoring
- [ ] 2.6 Add a test confirming viewing results leaves `Competition.winner` unset

## 3. Ranking submission — validation and atomicity

Spec: [`specs/project-ranking-ballot/spec.md`](specs/project-ranking-ballot/spec.md).

- [ ] 3.1 Add a failing test to `api/routers/test_my_review.py`: duplicate project IDs return 400 and leave the existing ballot intact
- [ ] 3.2 Reject duplicate IDs in `update_rankings` (`api/routers/my_review.py:143-197`) before any write
- [ ] 3.3 Add a failing test: a write failure part-way through leaves the previous ballot intact
- [ ] 3.4 Wrap the delete-then-`bulk_create` in `transaction.atomic`
- [ ] 3.5 Add a failing test: ranking update on an `ENDED` review returns 400
- [ ] 3.6 Extend the status guard from `COMPLETED` to `COMPLETED` or `ENDED`
- [ ] 3.7 Confirm existing partial-ballot tests (`test_my_review.py:386-418`, `:459-472`, `:474-483`) still pass unchanged

## 4. Seeded unranked pool ordering

- [ ] 4.1 Write failing tests: same reviewer gets a stable order across calls; two reviewers get different orders; order is independent of `created_at`
- [ ] 4.2 Implement the `sha256(user_id:competition_id:project_id)` keyed sort and apply it to unranked projects in `GET /api/my/reviews/competitions/{id}` (`api/routers/my_review.py:79-140`)
- [ ] 4.3 Confirm the response distinguishes ranked from unranked projects clearly enough for the client to split them without re-deriving order
- [ ] 4.4 Check the endpoint's query-count budget test (`test_my_review.py:314`) still holds

## 5. OpenAPI contract

- [ ] 5.1 Run `make extract-openapi` from `src/django-backend/`
- [ ] 5.2 Run `npm run generate-types` from `src/web-ui/`
- [ ] 5.3 Commit the regenerated `backend-openapi.json` and `src/web-ui/src/lib/api-types.ts` together with the backend change

## 6. Frontend — ranked list and pool

- [ ] 6.1 Fix the return type of `MyReviewClient.updateRankings` in `src/web-ui/src/lib/api/my-review.ts:37-48` — it returns `SuccessResponse`, not `ReviewCompetitionDetailResponse`
- [ ] 6.2 Replace the `sortByMyRanking` initial-ordering logic in `CompetitionReveal.tsx:57,227-234` with a split into ranked list and server-ordered pool
- [ ] 6.3 Split `RankingList.tsx` into a ranked list (drag + chevrons + remove) and a pool list (`+ Rank` per project); keep dnd-kit scoped to the ranked list only
- [ ] 6.4 Wire add/remove so added projects append to position 1 + current length, and removal closes the position gap
- [ ] 6.5 Add the responsive shell in `MyRanking.tsx` — side by side on wide screens, two tabs with a ranked count on narrow screens
- [ ] 6.6 Ensure `+ Rank` on the pool tab does not switch tabs, and updates the ranked-tab count
- [ ] 6.7 Update the instruction copy at `MyRanking.tsx:216-219`, which currently tells reviewers to drag to order every project
- [ ] 6.8 Add the empty-ballot confirmation to `SubmitRankingDialog.tsx`, stating plainly that no projects will be ranked
- [ ] 6.9 Flush the pending debounced save in `persistOrder` (`MyRanking.tsx:139-158`) before the `updateStatus("completed")` call
- [ ] 6.10 Verify `npm run lint` passes from `src/web-ui/`

## 7. Frontend tests

No tests exist for any ranking component today. `data-testid="ranked-card"` and `data-testid="rank-badge"` already exist in `RankingList.tsx` and are unreferenced.

- [ ] 7.1 Add review/ranking factories to `src/web-ui/src/test/factories.ts`
- [ ] 7.2 Test: a competition with no saved ballot renders an empty ranked list and every project in the pool
- [ ] 7.3 Test: adding from the pool appends to the bottom of the ranked list and removes it from the pool
- [ ] 7.4 Test: removing a middle entry closes the gap and returns the project to the pool
- [ ] 7.5 Test: reorder controls move a ranked project one position
- [ ] 7.6 Test: submitting an empty ballot requires confirmation, and cancelling leaves status unchanged
- [ ] 7.7 Test: reorder immediately followed by submit persists the reorder before the status change

## 8. Verification

- [ ] 8.1 Run `make ci` from the project root
- [ ] 8.2 Exercise the reviewer flow end to end against a running instance — rank 2 of 8, submit, reopen, confirm the other 6 are in the pool and not scored
- [ ] 8.3 Confirm two different test reviewers see different pool orders for the same competition
- [ ] 8.4 View the admin results page for a competition with mixed full and partial ballots; check the ranked-by column and pairwise grid read correctly
- [ ] 8.5 Confirm a closed historical competition still renders results and its stored `winner` is untouched
