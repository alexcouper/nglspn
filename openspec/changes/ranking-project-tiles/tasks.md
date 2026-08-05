Implementation order: backend first, because the frontend needs the regenerated types before it can render a category label. Within the backend, the prefetch fix lands before `_get_main_image` is deleted — see [design.md](design.md), "The ballot reuses `resolve_image_by_purpose`, with the prefetch fixed first". Getting that order wrong ships a window where the ballot renders images that are still uploading.

The backend is additive, so it can deploy on its own. Nothing here needs a coordinated release.

## 1. Ballot query — fix the prefetch before reusing the resolver

`get_reviewer_projects` prefetches `images` unfiltered and relies on `_get_main_image` filtering in Python. `resolve_image_by_purpose` does no such filtering. Spec: [`specs/project-image-purposes/spec.md`](specs/project-image-purposes/spec.md).

- [x] 1.1 Add a failing test in `src/django-backend/services/review/django_impl/test_query.py`: a project whose only image has `upload_status` other than `uploaded` yields no image on the reviewer's ballot
- [x] 1.2 Narrow the `images` prefetch in `services/review/django_impl/query.py` to `ProjectImage.objects.filter(upload_status="uploaded").prefetch_related("variants")`, matching `_base_queryset` in `services/project/django_impl/query.py`
- [x] 1.3 Add `.select_related("category")` to the same queryset
- [x] 1.4 Add a test asserting the ballot query issues no extra query per project for `category` (use `django_assert_num_queries`)

## 2. Ballot response — category and purpose-resolved images

Spec: [`specs/project-image-purposes/spec.md`](specs/project-image-purposes/spec.md).

- [x] 2.1 Write failing tests for the ballot endpoint: the response carries `category_name` for a categorised project and `None` for an uncategorised one
- [x] 2.2 Write a failing test asserting `in_use_image_url` prefers the `in_use`-purpose image over the main image, and falls back to the main image when no `in_use` image exists
- [x] 2.3 Add `category_name`, `in_use_image_url` and `hero_banner_url` to `ReviewProjectResponse` in `api/schemas/my_review.py`, keeping `main_image_url` and `main_image_variants`
- [x] 2.4 Rewrite `_project_response` in `api/routers/my_review.py` to populate them via `resolve_image_by_purpose`, and delete the now-unused `_get_main_image`
- [x] 2.5 Run `make lint` and `make test` from `src/django-backend/`

## 3. Regenerate the API contract

The repo foot-gun — the frontend cannot see the new fields until both commands have run. See [CONTRIBUTING.md](../../../CONTRIBUTING.md).

- [x] 3.1 `cd src/django-backend && make extract-openapi`
- [x] 3.2 `cd src/web-ui && npm run generate-types`
- [x] 3.3 Confirm `ReviewProjectResponse` in `src/web-ui/src/lib/api-types.ts` now carries the three new fields

## 4. Extract `ProjectTile`

Spec: [`specs/project-listing-discover/spec.md`](specs/project-listing-discover/spec.md).

- [x] 4.1 Create `src/web-ui/src/components/ProjectTile.tsx` taking `id`, `href`, `imageUrl`, `categoryName`, `title`, `tagline`, `dimmed`, with the markup currently inside `ArrivalCard`
- [x] 4.2 Clamp the title to 2 lines instead of `truncate`; keep the tagline at 2 lines
- [x] 4.3 Implement `dimmed`: drop `card-interactive`, mute the title and tagline
- [x] 4.4 Reduce `ArrivalCard` in `src/app/projects/sections/NewArrivalsSection.tsx` to a wrapper that maps `DiscoverProject` onto those props
- [ ] 4.5 Check the New Arrivals row visually with a title long enough to wrap — cards must stay equal height and the row must not go ragged

## 5. Rebuild the ballot cards

Spec: [`specs/project-ranking-ballot/spec.md`](specs/project-ranking-ballot/spec.md).

- [x] 5.1 Restructure `RankingCard` in `src/app/competitions/[id]/RankingList.tsx` as a flex row: `ProjectTile` in a `flex-1 min-w-0` wrapper, control column beside it
- [x] 5.2 Move the rank badge, drag handle (`sm` and up), and up/down arrows into that control column, keeping their current `aria-label`s and 44px mobile touch targets
- [x] 5.3 Move the remove button into the same column, below the arrows
- [x] 5.4 Drop the entry's `bg-white rounded-xl border` wrapper — `ProjectTile` carries the `card` surface
- [x] 5.5 Apply the same structure to the pool card in `PoolList`, with the "Rank" button in the control column
- [x] 5.6 Delete `CardImage` and `CardText`, and with them the ballot's `website_url` line
- [x] 5.7 Pass `dimmed` when `readOnly`, replacing the `bg-muted` treatment
- [x] 5.8 Confirm no button is nested inside the tile's `<Link>`

## 6. Frontend tests

- [x] 6.1 Extend `src/app/competitions/[id]/MyRanking.test.tsx`: a ranked card renders its full title and tagline text, not a truncated form
- [x] 6.2 Assert the category label renders when `category_name` is present and is absent when it is null
- [x] 6.3 Assert activating up / down / remove / add does not navigate, and that the card area links to the project page
- [x] 6.4 Assert a read-only ballot renders no reorder or remove controls but still shows title and tagline
- [x] 6.5 Run `npm run lint` and the web-ui test suite from `src/web-ui/`

## 7. Verify in the running app

Per [CLAUDE.md](../../../CLAUDE.md), using the credentials in `.env.claude`.

**Blocked on test data.** The database behind the running dev server holds four
competitions, all `closed` with one project each, and `test@example.com` has no
review assignment — so `/my-reviews` redirects and there is no ballot to open.
A ballot needs a competition in `voting` status with several projects and the
test user assigned as a reviewer.

- [ ] 7.1 Log in as the test reviewer and open a competition ballot at mobile width — confirm titles and taglines are no longer cut off
- [ ] 7.2 Add, reorder and remove a project; confirm autosave and submission still work
- [ ] 7.3 View a submitted ballot and confirm the dimmed treatment reads as inert
- [x] 7.4 Open the project listing page and confirm New Arrivals is unharmed — checked at desktop width; cards stay equal height, including one carrying a category label. Not yet seen with a title long enough to wrap (all seeded titles are short domains), which is what 4.5 needs.
- [x] 7.5 Run `make ci` from the project root — no root `Makefile` and no `scripts/ci/` exist; CLAUDE.md is stale on both. Ran the equivalents instead: `make lint` + `make test` in `src/django-backend` (903 passed) and `npm run lint` + `npm test` in `src/web-ui` (31 passed).
