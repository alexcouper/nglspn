## Context

Two screens render the same project and disagree about how.

`ArrivalCard` ([`NewArrivalsSection.tsx:32`](../../../src/web-ui/src/app/projects/sections/NewArrivalsSection.tsx)) is a vertical tile: a 4:3 image, then category label, title, tagline. Because the image is above the text, the text gets the card's full width.

`RankingCard` and the pool card ([`RankingList.tsx`](../../../src/web-ui/src/app/competitions/[id]/RankingList.tsx)) are horizontal rows. The text column is what is left after a rank/arrow rail, a `w-16 sm:w-36` image, and a `min-w-[44px]` remove button — inside a panel that is only half the page at `lg`. `CardText` then applies `sm:truncate` to the title and `line-clamp-2` to the tagline. There is no width at which this reads well.

The two screens are fed by different schemas. `DiscoverProjectResponse` has `icon_url` / `hero_banner_url` / `in_use_image_url` / `category_name`; `ReviewProjectResponse` has `main_image_url` / `main_image_variants` / `website_url` and no category. So sharing a component means either a component that knows both types, or a component that knows neither.

The backend already has one image-resolution routine, `resolve_image_by_purpose` ([`services/project/django_impl/query.py:80`](../../../src/django-backend/services/project/django_impl/query.py)), but the ballot does not use it — `api/routers/my_review.py:39` has a private `_get_main_image` instead.

## Goals / Non-Goals

**Goals:**

- One component renders a project card, used by both the listing and the ballot.
- Ballot titles and taglines are readable in full, on mobile in particular.
- The ballot's image and category come from the same resolution the listing uses, so the two screens cannot drift apart again.
- Extending the review response does not break its existing consumers.

**Non-Goals:**

- Changing ballot mechanics — add, remove, reorder, autosave, submission, pool ordering are all untouched.
- Changing the two-panel-at-`lg` / tabs-on-mobile shell.
- Unifying every project card in the app. `CategoryCard`, the Featured hero cards, and `CompetitionReveal` keep their own layouts; they are genuinely different designs, not accidental drift.
- Reducing the tile's own proportions. The 4:3 image is kept; the card's footprint is contained by capping its width instead (see Decisions).

## Decisions

### `ProjectTile` takes primitive props, not an API type

The shared component lives at `src/web-ui/src/components/ProjectTile.tsx` and accepts `id`, `href`, `imageUrl`, `categoryName`, `title`, `tagline`, `dimmed` — all plain values. Each caller maps its own response type down to those props.

*Alternative considered:* type the component against `DiscoverProject` and have the ballot construct a partial one. Rejected — it makes the review screen depend on the discover schema, so every discover field addition becomes a ballot concern, and the compiler stops helping once the object is cast.

*Alternative considered:* a union type. Rejected — it pushes a discriminant and two field-access paths into the component for no gain over seven props.

`id` is a separate prop rather than derived from `href` because `GradientPlaceholder` seeds its gradient from the project id, and the two screens build different hrefs.

### The title clamp changes on the listing page too

`ProjectTile` clamps the title to 2 lines. The listing card currently truncates to 1, so this is a visible change to a screen nobody complained about.

Taking it anyway: a truncated title is a bug on both screens, and a per-caller `titleLines` prop would encode the inconsistency the change exists to remove. The row stays tidy because `HorizontalScroll` is `flex gap-4` ([`HorizontalScroll.tsx:34`](../../../src/web-ui/src/components/HorizontalScroll.tsx)) with default `align-items: stretch`, so cards already equalise height; a second title line consumes card space rather than making the row ragged.

### Controls sit outside the card, not on top of it

The ballot entry becomes a flex row: `ProjectTile` in a `flex-1 min-w-0` wrapper, and a fixed control column beside it holding the rank badge, drag handle (`sm` and up), up/down arrows and remove — or the "Rank" button for pool entries.

*Alternative considered:* overlay the rank badge on the image and put controls in a footer strip inside the card. Rejected — the tile is a `<Link>`, and nesting buttons inside an anchor is invalid HTML with genuinely bad keyboard and screen-reader behaviour. Keeping controls outside the link means no workaround is needed.

The entry's own `bg-white rounded-xl border` wrapper is dropped; `ProjectTile` already carries the `card` surface. Without this the ballot would show a bordered box inside a bordered box.

`CardImage` and `CardText` are deleted rather than adapted — everything they do is now `ProjectTile`'s job.

### The ballot card is a tile on narrow screens and a row on wide ones

`ProjectTile` takes `layout`. The listing uses the default `"tile"`; the ballot passes `"row-when-wide"`, which stacks below `sm` and lays image beside text above it.

Browsing and ranking are different tasks. A tile is a browsing card — it wins attention for one project at a time. Ranking is comparison, and what helps most is seeing the whole ballot at once. Measured at `lg`: as tiles a six-project ballot was 1590px and you could hold three in view; as rows it is 476px and the whole thing fits one screen.

Rows were the original layout and they failed, but not because rows are wrong — the title carried `sm:truncate` and a 144px image sat inside a half-page panel. With the truncation gone and the image at 140px, the row's text column measures 241px at `lg`, within a pixel of the listing card's 240px. So the ballot row is exactly as forgiving as the listing tile, which is the promise the spec makes.

Below `sm` there is no width for a row that does not clip, so it stays a tile, capped at `max-w-[240px]` — a 4:3 image stretched wider makes each entry ~300px tall. The cap lifts at `sm` where the row wants the panel. `w-full` with `max-w` rather than a fixed `w-[240px]` so the tile shrinks on very narrow screens instead of forcing horizontal overflow.

### Controls are split three ways, because a row has no room for a stack of five

At ~102px a row is shorter than a vertical stack of five 44px controls. Left as one column, the controls — not the card — would set the entry height, undoing the compaction. They are split by what each one is for:

- **Rank number** — before the card. A ranked list is scanned by number; with the badge trailing, the sequence ran down the far right edge past the content. Leading with it means 1‑2‑3‑4 reads down the left, as an ordered list should.
- **Reorder** (`^` / `=` / `v`) — a narrow column after the card. Measured 24px wide and 72px tall against a 102px row, so the card governs the height.
- **Remove** — the card's own top-right corner.

Together these took the control gutter from 144px to 24px, which moved the text column from 241px to 694px at the width measured. Taglines that previously wrapped to two lines now fit on one.

### The remove button overlays the card without being inside its link

`ProjectTile` renders a `<Link>`, and a `<button>` inside an `<a>` is invalid HTML that traps keyboard users on the link. So the remove button is positioned `absolute` over the card's corner while remaining a **DOM sibling** of the anchor — the tile's wrapper carries `relative`, and the button follows the tile rather than nesting in it. Visually in the card, structurally beside it.

It carries `bg-white/85 backdrop-blur-sm` because the corner sits over the image in tile layout and over white in row layout; a bare icon would disappear against one or the other.

### Read-only is a `dimmed` prop, not a second card

Today read-only entries swap to `bg-muted` with muted text. That becomes `dimmed` on the tile: drop `card-interactive`, mute the text. One code path, one place to change the treatment.

### The ballot reuses `resolve_image_by_purpose`, with the prefetch fixed first

`_project_response` ([`my_review.py:52`](../../../src/django-backend/api/routers/my_review.py)) switches to `resolve_image_by_purpose` and `_get_main_image` goes away.

This is only safe once the prefetch is fixed. `resolve_image_by_purpose` does no `upload_status` filtering — it relies on the caller having filtered, which the discover path does at the queryset level ([`query.py:55`](../../../src/django-backend/services/project/django_impl/query.py)). The ballot query prefetches `images` unfiltered ([`services/review/django_impl/query.py:82`](../../../src/django-backend/services/review/django_impl/query.py)) and compensates in Python inside `_get_main_image`. Delete that Python filter without narrowing the prefetch and the ballot starts showing images that are still uploading.

So the prefetch is narrowed to `upload_status="uploaded"` in the same step. That also brings the code in line with what `project-image-purposes` already claims ("a project has no uploaded images → null").

`select_related("category")` is added to the same queryset. Without it, `category_name` is one query per project on every ballot load.

### Review response fields are added, not replaced

`ReviewProjectResponse` gains `category_name`, `in_use_image_url`, `hero_banner_url`. `main_image_url` and `main_image_variants` stay, because [`CompetitionReveal.tsx:228`](../../../src/web-ui/src/app/competitions/[id]/CompetitionReveal.tsx) and the reviewer project-detail page read them. Additive, so no consumer breaks and no coordinated deploy is needed.

`website_url` stays on the response — the reviewer detail page uses it — but the ballot card stops rendering it, since the listing tile has no equivalent.

## Risks / Trade-offs

- **A 4:3 image at full panel width makes ballot entries tall.** Confirmed in the running app and resolved by the row layout (see Decisions). Entries went 300px → 265px (width cap) → 102px (rows).

- **The row's 241px text column is no more forgiving than the listing card's 240px.** A tagline too long for two lines still clamps. → Accepted, and deliberate: the spec's promise is that the ballot shows *as much as the listing does*, not more. Both surfaces clamp at the same width, so neither can drift ahead of the other.

- **`ProjectTile` now has two layouts, so a change to one can regress the other.** → The breakpoint behaviour is pure CSS on one component rather than two components to keep in sync, and the listing keeps the default so its markup is unchanged.

- **The listing page changes without having been the complaint.** A 2-line title shifts New Arrivals cards for every visitor. → Contained by `align-items: stretch` keeping heights equal, and by the fact that most titles fit on one line and are unaffected. Verify visually on the listing page, not only on the ballot.

- **Deleting `_get_main_image` silently weakens the upload filter if the prefetch change is missed.** The two edits are in different files and different layers. → They are a single task in `tasks.md`, and a backend test asserts a non-uploaded image is never returned.

- **`project-ranking-ballot` has no base spec yet.** It is defined by the pending [`less-biased-project-ranking`](../less-biased-project-ranking/proposal.md) change (implemented, not archived). This change's delta is written as `ADDED`, which validates today, but the two capabilities only merge cleanly once that change is archived. → Archive `less-biased-project-ranking` before archiving this one.

- **Forgetting the OpenAPI regeneration leaves the frontend unable to see the new fields.** The repo's standing foot-gun. → It is an explicit task, and the TypeScript build fails on the missing properties rather than failing silently at runtime.

## Migration Plan

No data model change, no migration, no coordinated deploy. The backend fields are additive, so the backend can ship before the frontend; the frontend renders the category label only when the field is present.

Rollback is a revert. Nothing is written differently and no stored data changes shape.

## Open Questions

None. The image aspect (4:3, matching the listing) and the data fidelity (add `category_name` plus purpose-resolved images to the review endpoint rather than making do with `main_image_url`) were both settled before this change was written.
