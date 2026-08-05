Implementation order: the pure tally functions first (they carry the correctness argument and need no ORM), then the service layer that wraps them, then the thin router and admin callers, then the frontend. Backend and frontend must ship together — see [design.md](design.md) Migration Plan.

Ranking currently bypasses the service layer entirely — `api/routers/my_review.py` and `CompetitionAdmin.voting_results_view` both touch `ProjectRanking` directly. Groups 1–4 move the whole domain behind `services/review/`; after them, no router or admin view imports `ProjectRanking`.

## 1. Tally core — pure functions

Pure functions over plain data, no ORM, inside the service package. Spec: [`specs/competition-vote-tally/spec.md`](specs/competition-vote-tally/spec.md).

- [ ] 1.1 Write failing tests for ballot reduction in `src/django-backend/services/review/test_tally.py`: full ballot, partial ballot, empty ballot, unranked pairs contribute nothing
- [ ] 1.2 Write a failing test asserting truncation neutrality — `[A,B]` and `[A,B,C,D]` contribute an identical A-over-B count
- [ ] 1.3 Implement `reduce_ballots_to_margins(ballots, eligible_project_ids)` in `src/django-backend/services/review/tally.py` returning a pairwise margin matrix
- [ ] 1.4 Define the `OrderingRule` `Protocol` — `(margins) -> list[list[ProjectId]]`, ranked tiers so ties are a first-class result — plus the `MarginMatrix` and `ProjectId` type aliases
- [ ] 1.5 Write failing tests for the ordering rule: Condorcet winner first, the 3-cycle from design.md resolves to A/B/C, equal strongest paths land in the same tier
- [ ] 1.6 Implement `schulze_order(margins)` conforming to `OrderingRule`, using the Floyd–Warshall strongest-path computation
- [ ] 1.7 Add a test asserting an ordering rule can be exercised on a hand-built matrix with no ballots, reviewers or competitions in sight
- [ ] 1.8 Add a test asserting ballot reduction produces a complete matrix without invoking any ordering rule
- [ ] 1.9 Add a test asserting ineligible project IDs referenced by a ballot are dropped from both the matrix and the ordering
- [ ] 1.10 Confirm `test_tally.py` needs no `django_db` marker — these tests must run without a database

## 2. Review service — query side

`reviews` exists on `HandlerServices` but not on `QueryServices`; there is no `ReviewQueryInterface` yet.

- [ ] 2.1 Create `services/review/query_interface.py` with `ReviewQueryInterface` (`ABC` + `@abstractmethod`, matching `services/discussions/query_interface.py`)
- [ ] 2.2 Declare `get_competition_tally(competition_id)` returning ranked tiers plus per-project support signals — first-place count, ranked-by count, mean position — and the margin matrix
- [ ] 2.3 Declare `get_reviewer_projects(user_id, competition_id)` returning the reviewer's ranked projects in position order plus their unranked pool in stable per-reviewer order
- [ ] 2.4 Implement both in `services/review/django_impl/query.py` as `DjangoReviewQuery`, delegating computation to `tally.py`, typed against `OrderingRule` rather than importing `schulze_order` at the call site
- [ ] 2.5 Exclude non-`COMPLETED` reviewers and `REJECTED`/`ICE_BOX` projects inside the query, not in callers
- [ ] 2.6 Register `reviews: ReviewQueryInterface` on `QueryServices` in `services/__init__.py` and re-export from `services/review/django_impl/__init__.py`
- [ ] 2.7 Add `services/review/django_impl/test_query.py` covering both methods against real ORM data

## 3. Review service — write side

- [ ] 3.1 Add `replace_ballot(user_id, competition_id, project_ids)` to `ReviewHandlerInterface` (`services/review/handler_interface.py`)
- [ ] 3.2 Write failing tests in `services/review/django_impl/test_handler.py`: duplicate IDs rejected before any write; a mid-write failure leaves the previous ballot intact; an empty list clears the ballot
- [ ] 3.3 Implement `replace_ballot` on `DjangoReviewHandler` — reject duplicates first, then delete-and-`bulk_create` inside `transaction.atomic`, positions numbered contiguously from 1
- [ ] 3.4 Move the eligibility check (submitted IDs ⊆ competition's non-excluded projects) into the handler
- [ ] 3.5 Add a failing test then extend the status guard from `COMPLETED` to `COMPLETED` or `ENDED`

## 4. Thin the callers

Spec: [`specs/project-ranking-ballot/spec.md`](specs/project-ranking-ballot/spec.md).

- [ ] 4.1 Rewrite `update_rankings` (`api/routers/my_review.py:143-197`) to validate the payload shape and call `HANDLERS.reviews.replace_ballot`, mapping handler errors to 400
- [ ] 4.2 Rewrite the reviewer detail endpoint (`api/routers/my_review.py:79-140`) to call `REPO.reviews.get_reviewer_projects` instead of querying `ProjectRanking` and `competition.projects` directly
- [ ] 4.3 Decide and implement the response shape that lets the client split ranked from pool without re-deriving order — this blocks groups 7 and 8, settle it before starting them
- [ ] 4.4 Replace the Borda loop in `CompetitionAdmin.voting_results_view` (`apps/projects/admin.py:814-884`) with a call to `REPO.reviews.get_competition_tally`, leaving the view as template plumbing only
- [ ] 4.5 Build the view context from the service result: rank (flattening tiers so a shared tier shares a rank), first-place count, ranked-by count, mean position among rankers, and the pairwise margin grid
- [ ] 4.6 Rewrite `templates/admin/projects/competition/voting_results.html` — replace the 1st..Nth position histogram and the prose describing Borda scoring
- [ ] 4.7 Rewrite `tests/test_voting_results.py` against the new rule — delete the Borda assertions, keep the staff-only and no-completed-voters cases, add partial-ballot and thin-support cases
- [ ] 4.8 Add a test confirming viewing results leaves `Competition.winner` unset
- [ ] 4.9 Confirm existing partial-ballot tests (`test_my_review.py:386-418`, `:459-472`, `:474-483`) still pass unchanged
- [ ] 4.10 Check the detail endpoint's query-count budget test (`test_my_review.py:314`) still holds after the service indirection
- [ ] 4.11 Grep to confirm no router or admin module imports `ProjectRanking` any more
- [ ] 4.12 Verify `make lint` and `make test` pass from `src/django-backend/`

## 5. Seeded unranked pool ordering

Implemented inside `DjangoReviewQuery.get_reviewer_projects` (task 2.3), not in the router.

- [ ] 5.1 Write failing tests: same reviewer gets a stable order across calls; two reviewers get different orders; order is independent of `created_at`
- [ ] 5.2 Implement the `sha256(user_id:competition_id:project_id)` keyed sort over the unranked pool
- [ ] 5.3 Add a test asserting the ranked portion is returned in saved position order and is unaffected by the keyed sort

## 6. OpenAPI contract

- [ ] 6.1 Run `make extract-openapi` from `src/django-backend/`
- [ ] 6.2 Run `npm run generate-types` from `src/web-ui/`
- [ ] 6.3 Commit the regenerated `backend-openapi.json` and `src/web-ui/src/lib/api-types.ts` together with the backend change

## 7. Frontend — ranked list and pool

- [ ] 7.1 Fix the return type of `MyReviewClient.updateRankings` in `src/web-ui/src/lib/api/my-review.ts:37-48` — it returns `SuccessResponse`, not `ReviewCompetitionDetailResponse`
- [ ] 7.2 Replace the `sortByMyRanking` initial-ordering logic in `CompetitionReveal.tsx:57,227-234` with a split into ranked list and server-ordered pool
- [ ] 7.3 Split `RankingList.tsx` into a ranked list (drag + chevrons + remove) and a pool list (`+ Rank` per project); keep dnd-kit scoped to the ranked list only
- [ ] 7.4 Wire add/remove so added projects append to position 1 + current length, and removal closes the position gap
- [ ] 7.5 Add the responsive shell in `MyRanking.tsx` — side by side on wide screens, two tabs with a ranked count on narrow screens
- [ ] 7.6 Ensure `+ Rank` on the pool tab does not switch tabs, and updates the ranked-tab count
- [ ] 7.7 Update the instruction copy at `MyRanking.tsx:216-219`, which currently tells reviewers to drag to order every project
- [ ] 7.8 Add the empty-ballot confirmation to `SubmitRankingDialog.tsx`, stating plainly that no projects will be ranked
- [ ] 7.9 Flush the pending debounced save in `persistOrder` (`MyRanking.tsx:139-158`) before the `updateStatus("completed")` call
- [ ] 7.10 Verify `npm run lint` passes from `src/web-ui/`

## 8. Frontend tests

No tests exist for any ranking component today. `data-testid="ranked-card"` and `data-testid="rank-badge"` already exist in `RankingList.tsx` and are unreferenced.

- [ ] 8.1 Add review/ranking factories to `src/web-ui/src/test/factories.ts`
- [ ] 8.2 Test: a competition with no saved ballot renders an empty ranked list and every project in the pool
- [ ] 8.3 Test: adding from the pool appends to the bottom of the ranked list and removes it from the pool
- [ ] 8.4 Test: removing a middle entry closes the gap and returns the project to the pool
- [ ] 8.5 Test: reorder controls move a ranked project one position
- [ ] 8.6 Test: submitting an empty ballot requires confirmation, and cancelling leaves status unchanged
- [ ] 8.7 Test: reorder immediately followed by submit persists the reorder before the status change

## 9. Verification

- [ ] 9.1 Run `make ci` from the project root
- [ ] 9.2 Exercise the reviewer flow end to end against a running instance — rank 2 of 8, submit, reopen, confirm the other 6 are in the pool and not scored
- [ ] 9.3 Confirm two different test reviewers see different pool orders for the same competition
- [ ] 9.4 View the admin results page for a competition with mixed full and partial ballots; check the ranked-by column and pairwise grid read correctly
- [ ] 9.5 Confirm a closed historical competition still renders results and its stored `winner` is untouched
