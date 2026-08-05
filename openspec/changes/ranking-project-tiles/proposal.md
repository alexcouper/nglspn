## Why

A reviewer ranking projects sees a worse rendering of each project than a visitor browsing the same project on the listing page. The ballot card ([`RankingList.tsx`](../../../src/web-ui/src/app/competitions/[id]/RankingList.tsx)) is a horizontal row whose text column is squeezed between a rank/arrow rail, a 64px–144px image, and a 44px remove button — and the ranked panel is only half the page at `lg`. The title is `sm:truncate` and the tagline is `line-clamp-2`, so both get cut. On mobile a title as short as "Puffin Tracker" wraps to two lines and the tagline reads "Monitorir Iceland…".

That is the wrong place to lose information. The reviewer is the one person on the site being asked to judge these projects against each other, and they see less about each one than a casual browser does.

The listing tile ([`NewArrivalsSection.tsx:32`](../../../src/web-ui/src/app/projects/sections/NewArrivalsSection.tsx)) already solves this by stacking vertically: the image sits on top and the text gets the full card width. Reusing that tile on the ballot fixes the truncation and stops the two screens drifting apart.

## What Changes

**Shared tile**

- The markup inside `ArrivalCard` becomes a `ProjectTile` component in `src/web-ui/src/components/`. It takes plain props (`id`, `href`, `imageUrl`, `categoryName`, `title`, `tagline`, `dimmed`) rather than an API type — the listing and the ballot are served by different response schemas (`DiscoverProjectResponse` vs `ReviewProjectResponse`) and neither should own the other's rendering.
- The tile's title changes from `truncate` to a 2-line clamp. This is the truncation being complained about. It is safe on the listing page: `HorizontalScroll` is a `flex` row with default `align-items: stretch` ([`HorizontalScroll.tsx:34`](../../../src/web-ui/src/components/HorizontalScroll.tsx)), so a two-line title eats into the card instead of making the row ragged.

**Ballot cards**

- Ranked and pool cards become a `ProjectTile` plus a control column to its right, instead of a horizontal row. The rank badge, drag handle, up/down arrows and remove action stack in that column; the pool card gets the "Rank" button there.
- The card's own `bg-white rounded-xl border` wrapper is dropped — `ProjectTile` already carries the `card` surface, and the controls now sit outside it, so the tile stays a single clean link target.
- The `website_url` line is removed from ballot cards. The listing tile has no equivalent and keeping it would make the ballot tile a hybrid of the two designs.
- Read-only ballots (submitted or ended) keep their dimmed treatment via the tile's `dimmed` prop rather than a separate muted card.

**Review API**

- `ReviewProjectResponse` gains `category_name`, `in_use_image_url` and `hero_banner_url`, so the ballot tile can render the same category label and the same resolved image as the listing tile. `main_image_url` and `main_image_variants` stay for now. Additive only, no **BREAKING** marker.

  > **Correction.** Those two fields were kept on the grounds that `CompetitionReveal.tsx` and the reviewer project-detail page still read them. They do not: `CompetitionReveal.tsx:226` and `:270` take `CompetitionProject`, and the detail page uses `ReviewProjectDetailResponse` — both different schemas. Nothing read them off `ReviewProject`, and [`fix-ballot-submit-and-boundaries`](../fix-ballot-submit-and-boundaries/proposal.md) removes them.
- The reviewer ballot query gains `select_related("category")`; without it the new field is an N+1 across every project in the competition.
- **Bug fix**: the reviewer ballot query prefetches `images` unfiltered ([`services/review/django_impl/query.py:82`](../../../src/django-backend/services/review/django_impl/query.py)), while `resolve_image_by_purpose` does no `upload_status` filtering of its own ([`services/project/django_impl/query.py:80`](../../../src/django-backend/services/project/django_impl/query.py)) — it relies on the caller having filtered, as the discover path does. Reusing it on the ballot as-is would surface images that are still uploading. The ballot prefetch is narrowed to `upload_status="uploaded"` to match discover and to match what the `project-image-purposes` spec already claims.
- Requires OpenAPI regeneration and `npm run generate-types`, per [CONTRIBUTING.md](../../../CONTRIBUTING.md).

**Not changing**

- The two-panel-at-`lg` / tabs-on-mobile ballot layout stays as it is.
- The 4:3 image aspect is kept rather than shortened, matching the listing tile exactly.

**The ballot card is a tile on narrow screens and a row on wide ones**

`ProjectTile` takes a `layout` prop. The listing keeps the tile at every width; the ballot stacks below `sm` and lays out side by side above it.

Ranking is a comparison task, and the thing that helps most is seeing the whole ballot at once. Tiles made a six-project ballot 1590px of scroll; as rows it is 476px, one screen. The row's text column measures 241px at `lg` — within a pixel of the listing card's 240px — so it clips no sooner than the listing does. Below `sm` there is no width for a row that does not clip, so it stays a tile, capped at 240px.

The controls split by purpose for the same reason — five stacked 44px controls are taller than a 102px row, so one column would set the entry height and undo the compaction. The rank number leads the entry, so the list is scanned by number down its left edge; reorder (`^` / `=` / `v`) follows the card in a 24px column; remove sits in the card's own top corner, drawn over the card but kept a DOM sibling of its link. Together this took the control gutter from 144px to 24px and the text column from 241px to 694px.

## Capabilities

### New Capabilities

_(none — this reshapes existing surfaces)_

### Modified Capabilities

- `project-ranking-ballot`: adds a requirement that ballot cards present a project with the same untruncated title, tagline and category label as the listing tile, with ranking controls beside the card rather than inside it.
- `project-listing-discover`: the New Arrivals card title wraps to two lines instead of truncating to one.
- `project-image-purposes`: purpose-resolved image URLs are no longer listing-only — the reviewer ballot endpoint returns them too, and resolution is stated to consider only uploaded images.

## Impact

- **Sequencing**: `project-ranking-ballot` is defined by the pending [`less-biased-project-ranking`](../less-biased-project-ranking/proposal.md) change, which is fully implemented (61/61 tasks) but not archived, so no `openspec/specs/project-ranking-ballot/` exists yet. This change's delta against that capability only resolves cleanly once that change is archived. Archive it first, or accept that `openspec validate` flags the missing base spec until then.
- **Web UI**: new `src/web-ui/src/components/ProjectTile.tsx`; `NewArrivalsSection.tsx` reduced to a wrapper; `RankingList.tsx` — both `RankingCard` and `PoolList` restructured, `CardImage`/`CardText` deleted.
- **Django backend**: `api/schemas/my_review.py` (three new fields), `api/routers/my_review.py` (`_project_response`, `_get_main_image` superseded by `resolve_image_by_purpose`), `services/review/django_impl/query.py` (prefetch and `select_related`).
- **OpenAPI**: `backend-openapi.json` regenerated, TS types regenerated. Additive, so no frontend consumer breaks.
- **Tests**: backend — the ballot response carries the category name, prefers the `in_use` image over the main image, and never picks a non-uploaded image. Frontend — `MyRanking.test.tsx` extended to assert the full title and tagline render and the category label is present.
- **Data model**: none. No migration.
