Implementation order: the submit guard first, because it is the only finding with a live failure mode and it depends on nothing else. Then the backend boundary work, then the contract regeneration, then the frontend cleanup that needs the regenerated types. The tab semantics and the branch split are independent and can land in any order.

Sections 2 and 3 must ship together — section 2 shrinks the response and the frontend will not typecheck until section 3 has run.

## 1. Submission stops when the ballot write fails

Design: [design.md](design.md), "A failed ballot write aborts submission". Spec: [`specs/project-ranking-ballot/spec.md`](specs/project-ranking-ballot/spec.md).

- [x] 1.1 Add a failing test in `src/web-ui/src/app/competitions/[id]/MyRanking.test.tsx`: with `updateRankings` rejecting, reorder then submit, and assert `updateStatus` is never called and the review is still editable
- [x] 1.2 Add a failing test asserting the reviewer sees a message saying the ranking was not saved and was not submitted
- [x] 1.3 Change `saveNow` in `MyRanking.tsx` to return `Promise<boolean>`, keeping the `setSaveError` side effect for the autosave path
- [x] 1.4 Have `flushPendingSave` return that boolean — `true` when there was nothing pending
- [x] 1.5 Guard `handleSubmit`: return with `statusError` set when the flush reports failure, before `updateStatus`
- [x] 1.6 Confirm the existing `"persists the reorder before the status change"` test still passes — autosave behaviour must not change
- [x] 1.7 `cd src/web-ui && npx vitest run`

## 2. Ballot image resolution moves into the query layer

Design: [design.md](design.md), "Ballot image resolution moves into the query layer" and "Drop `main_image_url` and `main_image_variants` from the ballot response".

- [x] 2.1 Add a failing test in `src/django-backend/services/review/django_impl/test_query.py`: `get_reviewer_projects` returns items carrying `in_use_image_url`, `hero_banner_url` and `category_name`
- [x] 2.2 Add `ReviewProjectItem` to `services/review/query_interface.py` (`project`, `hero_banner_url`, `in_use_image_url`, `category_name`), modelled on `DiscoverProjectItem`; change `ReviewerProjects.ranked` / `.pool` to lists of it
- [x] 2.3 Resolve the URLs inside `DjangoReviewQuery.get_reviewer_projects`, beside the `upload_status="uploaded"` prefetch that makes the resolution correct
- [x] 2.4 Remove `main_image_url` and `main_image_variants` from `ReviewProjectResponse` in `api/schemas/my_review.py`
- [x] 2.5 Reduce `_project_response` in `api/routers/my_review.py` to a field mapping; delete the `services.project.django_impl.query` import
- [x] 2.6 Delete `EXCLUDED_PROJECT_STATUSES` from `api/routers/my_review.py` and import it from `services.review.django_impl.query` for the remaining endpoints
- [x] 2.7 Update `api/routers/test_my_review.py` — the image assertions move from `main_image_url` to the resolved fields; keep `test_never_resolves_an_image_that_is_still_uploading`
- [x] 2.8 Confirm `get_competition_tally` and the admin results view are untouched
- [x] 2.9 Confirm the ballot endpoint still fits `django_assert_max_num_queries(10)`
- [x] 2.10 `cd src/django-backend && make lint && make test`

## 3. Regenerate the API contract

The repo foot-gun. The response shape shrinks, so the frontend cannot typecheck until both commands have run. See [CONTRIBUTING.md](../../../CONTRIBUTING.md).

- [x] 3.1 `cd src/django-backend && make extract-openapi`
- [x] 3.2 `cd src/web-ui && npm run generate-types`
- [x] 3.3 Confirm `ReviewProjectResponse` in `src/web-ui/src/lib/api-types.ts` no longer carries `main_image_url` or `main_image_variants`
- [x] 3.4 Commit `src/web-ui/backend-openapi.json` — `api-types.ts` is gitignored and must not be

## 4. Frontend catches up with the smaller response

- [x] 4.1 Drop `main_image_url` and `main_image_variants` from `makeReviewProject` in `src/web-ui/src/test/factories.ts`
- [x] 4.2 `npx tsc --noEmit` and fix anything still reading them off `ReviewProject` — `CompetitionReveal.tsx` reads them off `CompetitionProject` and must not change
- [x] 4.3 `cd src/web-ui && npm run lint && npx vitest run`

## 5. Tabs get real tab semantics

Design: [design.md](design.md), "The tabs get real tab semantics". Spec: [`specs/project-ranking-ballot/spec.md`](specs/project-ranking-ballot/spec.md).

- [x] 5.1 Add a failing test asserting each tab's `aria-controls` names a panel whose `id` matches and whose `role` is `tabpanel`
- [x] 5.2 Add a failing test asserting the left/right arrow keys move selection between the tabs
- [x] 5.3 Give each `TabButton` an `id` and `aria-controls`; give each panel `role="tabpanel"` and `aria-labelledby`
- [x] 5.4 Add roving `tabindex` — `0` on the selected tab, `-1` on the other
- [x] 5.5 Handle Left / Right / Home / End on the tablist
- [ ] 5.6 Check with VoiceOver on a narrow viewport that the unranked pool is reachable from its tab

## 6. Split out the Discord URL change

Design: [design.md](design.md), "The Discord URL change moves to its own branch". No code change.

- [ ] 6.1 Confirm the new invite (`KX7qmrwP7x`) is a non-expiring invite before it merges
- [ ] 6.2 `jj split` the Discord commit — `lib/constants.ts`, `Footer.tsx`, `app/about/contact/page.tsx`, `app/about/prizes/page.tsx` — onto its own branch
- [ ] 6.3 Confirm `democratic-ranking` no longer touches those four files

## 7. Verify

- [x] 7.1 ~~`make ci` from the project root~~ — there is no root `Makefile` and no `scripts/ci/`, so `CLAUDE.md` is stale on this. Ran the equivalent instead: `make lint` + `uv run pytest` (906 passed) in `src/django-backend/`, `npm run lint` (eslint + `tsc --noEmit`) and `npx vitest run` (42 passed) in `src/web-ui/`
- [ ] 7.2 Against a running instance: reorder a ballot with the ranking endpoint failing, press Submit, and confirm the review stays in progress and editable
- [ ] 7.3 Against a running instance: reorder and submit normally, and confirm the submitted order is the one on screen
- [x] 7.4 Fix the `CompetitionReveal.tsx:228` claim in [`ranking-project-tiles/proposal.md`](../ranking-project-tiles/proposal.md) — the fields it cites are read off `CompetitionProject`, not `ReviewProject`
