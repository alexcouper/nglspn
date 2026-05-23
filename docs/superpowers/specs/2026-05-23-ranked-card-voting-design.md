# Merge the ranking list and project grid into a single ranked-card surface

Date: 2026-05-23
Builds on: `docs/2026-05-11-rework-voting-ux.md` (PR #65)

## Problem

On the competition page during voting, an assigned reviewer sees two surfaces showing the same projects:

1. The `MyRanking` block — small rows with tiny thumbnails, drag handle, up/down chevrons.
2. The "All Projects" grid — image-led cards with title.

The list is interactive but visually undernourished; the grid is rich but inert. Duplication on a single page, and the user has to mentally cross-reference between them to know which card maps to which row.

## Goal

Replace both surfaces with one ranked column of image-led cards. The card is the project; the order is the rank; the handle is on the same element. For visitors who can't rank, the page stays close to what's on `main`.

## Non-goals

- Changing voting eligibility or who is assigned (still `CompetitionReviewer`).
- Rewriting the dnd-kit setup. Same sensors, same strategy, same persistence.
- Changing the project page itself.

## Scope rule — who sees what

The page composes per visitor state. Each visitor sees exactly one of the two layouts.

| Competition status | Visitor                              | Projects section layout      |
|--------------------|--------------------------------------|------------------------------|
| Not voting         | anyone                               | **A** — today's grid         |
| Voting             | logged-out                           | **A** — grid + login CTA     |
| Voting             | logged-in, not assigned              | **A** — grid (no CTA box)    |
| Voting             | assigned reviewer (any sub-state)    | **C** — ranked card column   |

"Assigned reviewer" covers `in_progress`, `completed`, and `ended` sub-states. The C layout renders for all three; only `in_progress` shows interactive controls.

## C layout — anatomy

One vertical column of image-led cards, one per row. Implemented as a single `RankingCard` component that takes a `variant: "L" | "R"` prop and re-uses the same data + handlers for both.

### Variant L — controls on the left (matches today's `RankingList` order)

```
┌─────────────────────────────────────────────────────┐
│  ⇕    ┌──────────────┐                              │
│  ↑   1│    image     │  Project A                   │
│  ↓    │              │  Tagline goes here           │
│       └──────────────┘  project-a.is                │
└─────────────────────────────────────────────────────┘
```

Order: `[drag handle] [chevrons] [rank number] [image] [title / tagline / url]`.

### Variant R — controls on the right

```
┌─────────────────────────────────────────────────────┐
│  ┌──────────────┐                                   │
│  │    image    1│  Project A                  ⇕    │
│  │              │  Tagline goes here          ↑    │
│  └──────────────┘  project-a.is               ↓    │
└─────────────────────────────────────────────────────┘
```

Order: `[image with rank badge overlaid bottom-right of image] [title / tagline / url] [drag handle] [chevrons]`.

### Card content (both variants)

- **Image**: `pickVariant(project.main_image_variants, "medium") ?? project.main_image_url`. Roughly 96–112px tall on mobile, ~140×200 on `sm:` and up. Sized similarly to today's "All Projects" thumbs but laid out horizontally inside the row.
- **Rank number**: large and unmissable. In L it's a numeric badge between chevrons and image; in R it overlays the image corner (same convention as the winner trophy badge in `CompetitionReveal.tsx`).
- **Title**: `project.title`. One line, truncated.
- **Tagline**: `project.tagline` (new field — see Backend section). Two lines max, `line-clamp-2`. Hidden if empty.
- **URL**: `project.website_url`. One line, truncated, muted.

### Sub-state styling

- **`in_progress`** — drag handle visible on `sm:+`, chevrons always visible, "Saving…" / "Saved" microcopy below the section header.
- **`completed`** — drag and chevrons gone; cards muted (closer to today's `ReadOnlyRow`). "Reopen ranking" link below the list.
- **`ended`** — same muted styling, no reopen affordance.

### Mobile (`< sm`)

- The right rail in variant R collapses to a horizontal strip below the title row (drag handle + chevrons inline), since the right column gets crowded at narrow widths.
- In variant L the controls stay in their own left column — drag handle still hidden on `< sm` (TouchSensor activates from row body) but the chevrons remain.
- Chevrons get 44×44 minimum hit targets on mobile.

## Page composition

For an **assigned reviewer during voting**:

```
[ Hero banner ]
[ Voting banner ]
[ "My Ranking" section header ]
  status pill · save indicator · layout toggle (when ?variants=on)
  microcopy ("Drag or use the up/down buttons to rank…")
[ Ranked column of large cards — variant L or R ]
[ Submit Ranking button  OR  Reopen ranking link ]
```

The "All Projects" section is **not rendered** for this visitor — the ranked cards are the project list.

For every other visitor (non-voting; or voting + not-assigned; or logged-out), the composition stays close to today's `main`:

- The **purple voting banner copy** branches on whether the visitor is a ranker:
  - Ranker: "Voting is in progress. Rank the projects below to help pick the winner."
  - Non-ranker: "Voting is in progress. Selected members are ranking the projects."
- The **`MyRanking` shell**:
  - Logged-out: shows a compact login CTA only (no "My Ranking" heading — there's nothing to rank).
  - Logged-in, not assigned: not rendered at all.
- The **"All Projects" grid** renders unchanged.

## Variant toggle

L and R ship together behind a `?variants=on` query param. With the param:

- A small radio chip group sits in the section header next to the status pill: `Layout: ( L )( R )`.
- Selection persists in `localStorage` (key `ranking-variant-pref`). Refreshes are stable.
- Query param overrides localStorage when both disagree, and writes back through it.
- Toggle disabled mid-drag (`isDragging` state from `DndContext`).

Without `?variants=on` the default is L (closer to today's RankingList muscle memory) and no toggle UI is shown.

Once a winner is picked, both the toggle UI and the unchosen variant come out in the same PR. The branch should make that deletion mechanical — one prop, one branch in JSX.

## Data flow & component changes

### Lifting the assignment flag

Today `MyRanking` figures out assignment from a 404 on `/api/my/reviews/competitions/{id}`. `CompetitionReveal` doesn't know. Suppressing "All Projects" cleanly needs the parent to know.

Approach: **hoist the my-review fetch to `CompetitionReveal`**. The parent owns:

- The competition data (already does).
- The my-review data (`null` while loading; `{ kind: "not-assigned" }` on 404; `{ kind: "ready", data }` on success; `{ kind: "error", message }` on other failures).

From those two pieces of state it decides:
- Which voting banner copy to render.
- Whether to render `<MyRanking>` and in what mode (logged-out CTA vs ranked cards).
- Whether to render the "All Projects" grid (skip when ranked cards render).

This avoids the grid flashing on screen before being hidden by a child component callback, and centralises the page composition in one file.

### Component file map

**Modified**

- `src/web-ui/src/app/competitions/[id]/CompetitionReveal.tsx`
  - Owns my-review fetch.
  - Branches the voting banner copy.
  - Skips "All Projects" when ranked cards render.
  - Passes my-review data into `<MyRanking>` instead of having it fetch.
- `src/web-ui/src/app/competitions/[id]/MyRanking.tsx`
  - Slimmed: section header + status pill + save indicator + variant toggle + submit/reopen.
  - No fetch; takes data + handlers as props.
  - Logged-out branch becomes a small compact CTA card (no shell header).
  - Not-assigned branch becomes `null` (rendered nothing).
- `src/web-ui/src/app/competitions/[id]/RankingList.tsx`
  - Rewritten as the big-card renderer.
  - Accepts `variant: "L" | "R"` and `readOnly`.
  - Single `RankingCard` sub-component contains both variants' markup behind a small layout switch.

**New (optional)**

- `src/web-ui/src/app/competitions/[id]/useVariantPref.ts` — small hook reading `?variants=on` and `localStorage`. Could live in `MyRanking.tsx` if it stays under ~30 lines; pull out if it grows.

**Unchanged**

- `SubmitRankingDialog.tsx`.
- `dnd-kit` setup (sensors, strategy, persistence debounce).
- All the redirects from `/my-reviews/*`.

## Backend additions

`ReviewProjectResponse` (`src/django-backend/api/schemas/my_review.py`) gains three fields:

| Field | Type | Why |
|-------|------|-----|
| `tagline` | `str` (nullable) | New requirement — shown under the title on the card |
| `slug` | `str \| None` | Card link goes to `/projects/[slug]`, matching the rest of the site, rather than `/projects/[id]` |
| `main_image_variants` | `list[ImageVariantResponse]` | `pickVariant(..., "medium")` for sharper imagery at row width |

The router (`src/django-backend/api/routers/my_review.py`) passes them through from the project object. The image-variant logic mirrors what `CompetitionProjectResponse.from_list_item` already does.

After the schema change:

```
cd src/django-backend && make extract-openapi
cd src/web-ui && npm run generate-types
```

These are additive — no existing consumer breaks. The `ApiRequestError.status` change from PR #65 stays in place; we depend on it for the 404 → "not assigned" mapping in the hoisted fetch.

## Interactions

### Drag

- `verticalListSortingStrategy` unchanged.
- Drop target is the whole card, not just the handle. On touch, press-delay TouchSensor triggers from anywhere on the row.
- The card root is `<div>`, not a link. Only the title + image are clickable links to `/projects/[slug]`. Drag handle, chevrons, and surrounding row chrome don't navigate. Avoids the "tried to drag, navigated away" failure mode.
- Dragging row: `opacity: 0.5`, faint accent border on the hover target. Matches dnd-kit defaults.

### Chevrons

- `moveBy(index, ±1)` as today, disabled at the ends.
- 44×44 hit targets on mobile.

### Save

- Existing 500ms debounce on each reorder. "Saving…" / "Saved" / "Failed to save rankings" microcopy in the section header.

### Submit / reopen

- Submit button below the list opens `SubmitRankingDialog` unchanged.
- After confirm: cards switch to read-only styling, button is replaced with "Reopen ranking" link that calls `updateStatus("in_progress")`.
- `ended` status: read-only, no reopen.

## Edge cases

| Case | Behaviour |
|------|-----------|
| Zero projects | "No projects in this competition." empty-state card. No submit button. |
| One project | Single ranked card at rank 1; chevrons disabled both ends; submit still works. |
| `my_ranking` null on a newly added project | Sorted to the bottom (existing logic in `MyRanking.tsx`), gets the next rank. |
| Load error on my-review fetch | Section shows the existing red error banner; "All Projects" grid still renders below (so the page isn't fully broken). |
| Variant query param + localStorage disagree | Query param wins; localStorage is updated. |
| Toggle clicked mid-drag | Toggle disabled while `isDragging` is true. |

## Testing

### Unit / RTL

- `RankingCard` renders title, tagline, URL, image, rank for both variants.
- Variant L renders controls before image; variant R renders controls after image. Snapshot or specific order assertion.
- Chevrons disabled at index 0 (up) and index n−1 (down).
- Click on title navigates; click on drag handle and chevrons does not navigate.
- `onReorder` called with the expected `arrayMove` result on chevron click.

### Backend

- `ReviewProjectResponse` round-trips `tagline`, `slug`, `main_image_variants`.
- `GET /api/my/reviews/competitions/{id}` returns the new fields populated for an assigned reviewer.

### Manual / Playwright

Assigned reviewer flow:
1. Land on competition page → see "My Ranking" header, ranked cards (variant L), microcopy, submit button.
2. Drag card 3 to position 1 → see "Saving…" then "Saved".
3. Toggle to variant R via `?variants=on` chip → same data, different layout.
4. Tap up/down chevrons on mobile (Playwright touch emulation) → reorder, save.
5. Submit → confirmation dialog → status pill shows "Submitted", cards muted, "Reopen ranking" present.
6. Reopen → back to interactive cards.

Non-ranker flows:
- Logged-out: voting banner shows non-ranker copy; small login CTA visible; "All Projects" grid below.
- Logged-in, not assigned: no `MyRanking` shell rendered; non-ranker banner copy; grid below.

iOS Safari real-device check: drag from row body, press-delay, chevron fallback. Same caveat as PR #65 — full pass needs a real device.

## Reviewer notes

- **Why hoist the fetch instead of a callback**: a child component dictating sibling visibility means the sibling has a brief render before being hidden. Page composition belongs to the parent.
- **Why two variants and not one**: the user explicitly wants to compare control placement (left vs right) on real data before committing. Building both is cheap because the card body is shared; deleting the loser is a single-file edit.
- **Why `?variants=on` and not always-visible**: real reviewers shouldn't be presented with a "pick your layout" experience while we're still deciding. The toggle is for us, not them.
- **Why tagline now and not later**: the user asked for it on the card, and the card is being rebuilt regardless. Doing the schema change separately would leave the new card with empty space where the tagline goes.
- **Backwards compatibility**: all backend additions are additive. The `ApiRequestError.status` field added in PR #65 is leveraged by the hoisted fetch. No existing consumers break.
