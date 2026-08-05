## Why

Six findings came out of a review of the `democratic-ranking` branch, which ships [`less-biased-project-ranking`](../less-biased-project-ranking/proposal.md) and [`ranking-project-tiles`](../ranking-project-tiles/proposal.md). Nothing on that branch is wrong enough to block it — lint, 903 backend tests, 31 frontend tests and `tsc` all pass, and `make extract-openapi` produces no diff, so the API contract is in sync. But one finding is a real data-loss path and one is a boundary the branch itself was written to enforce.

The data-loss path: `saveNow` swallows a failed ranking PUT into a `saveError` banner ([`MyRanking.tsx:164`](../../../src/web-ui/src/app/competitions/[id]/MyRanking.tsx)), so `flushPendingSave` resolves whether or not the write landed, and `handleSubmit` goes straight on to `updateStatus(..., "completed")`. A reviewer who drags a project to the top and immediately submits, on a request that fails, gets their review locked against the *previous* ballot. That is the exact failure `less-biased-project-ranking` added the flush to prevent — the debounce race is closed, the failure race is not.

The boundary: `api/routers/my_review.py` imports `_variant_url` — a leading-underscore helper — out of `services/project/django_impl/query.py`. The branch's own design doc makes "no router or admin view touches the ORM layer directly" its stated goal, and this is that boundary crossed in a different shape.

The remaining four are cleanup that is cheap now and gets expensive once someone trusts the wrong thing.

## What Changes

**Ballot submission**

- **BREAKING** (behaviour, not API): a failed ballot write aborts submission. `saveNow` reports failure to its caller instead of only to state; `handleSubmit` stops before `updateStatus` and leaves the review editable with the error shown. Autosave keeps its current fire-and-forget behaviour — only the pre-submit flush becomes blocking.

**Service boundary**

- `ReviewerProjects` carries the resolved image URLs and category name, the way [`DiscoverProjectItem`](../../../src/django-backend/services/project/query_interface.py) already does. The router stops importing `_variant_url` and `resolve_image_by_purpose` and stops calling them; `_project_response` maps a DTO onto the schema and nothing else.
- `EXCLUDED_PROJECT_STATUSES` gets one home. The copy in `api/routers/my_review.py:40` is deleted and the remaining router endpoints use the service's.

**Ballot response**

- `main_image_url` and `main_image_variants` are removed from `ReviewProjectResponse`. No frontend consumer reads them — [`CompetitionReveal.tsx:226`](../../../src/web-ui/src/app/competitions/[id]/CompetitionReveal.tsx) and `:270` both take `CompetitionProject`, not `ReviewProject`, and every ballot render goes through `in_use_image_url || hero_banner_url`. **BREAKING** for the schema; requires OpenAPI regeneration and `npm run generate-types`, per [CONTRIBUTING.md](../../../CONTRIBUTING.md).

**Ballot tab semantics**

- The narrow-screen tabs claim `role="tablist"` / `role="tab"` with `aria-selected` but neither panel is a `tabpanel`, so a screen reader announces a tab and cannot reach what it controls. The panels get `role="tabpanel"`, `id`/`aria-controls`/`aria-labelledby`, and the tablist gets arrow-key navigation with roving `tabindex`.

**Branch hygiene**

- The Discord invite-URL change (`SITE_DISCORD_URL` in `lib/constants.ts`, plus `Footer.tsx`, `about/contact`, `about/prizes`) is unrelated to ranking. Split it onto its own branch so a live invite-link change is reviewed on its own terms. No code change — a rebase.

## Capabilities

### Modified Capabilities

- `project-ranking-ballot`: submission is refused while a ballot write is outstanding or failed, and the narrow-screen tabs expose real tab semantics.

## Impact

- **Sequencing**: `project-ranking-ballot` is defined by [`less-biased-project-ranking`](../less-biased-project-ranking/proposal.md) and modified by [`ranking-project-tiles`](../ranking-project-tiles/proposal.md), neither of which is archived, so no `openspec/specs/project-ranking-ballot/` exists yet. `openspec validate --strict` accepts the delta anyway, but it only *merges* onto a base once those two land — archive them in order before syncing this one.
- **Web UI**: `MyRanking.tsx` (`saveNow` signature, `handleSubmit` guard, tab wiring), `RankingList.tsx` (drops `main_image_*` from `ProjectCardTile`'s inputs — it already ignores them), `test/factories.ts` (`makeReviewProject` drops the two fields), `MyRanking.test.tsx` gains the failed-save case.
- **Django backend**: `services/review/query_interface.py` (`ReviewerProjects` becomes a list of DTOs, not `Project` rows), `services/review/django_impl/query.py` (resolves images in the query layer), `api/routers/my_review.py` (imports and `_project_response` shrink; one constant deleted), `api/schemas/my_review.py` (two fields removed).
- **OpenAPI**: regenerate `backend-openapi.json` and run `npm run generate-types` — the response shape shrinks.
- **Admin**: `get_competition_tally` still returns `Project` rows and is untouched; only `get_reviewer_projects` changes shape.
- **Data model**: none. No migration.
- **Tests**: the failed-save-blocks-submit case has no coverage today — the existing `"persists the reorder before the status change"` test only exercises the happy path. Backend tests move from asserting `main_image_url` on the ballot response to asserting the DTO carries the resolved URLs.
