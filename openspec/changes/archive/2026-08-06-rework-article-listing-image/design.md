## Context

`article-hero-cropping` landed yesterday (44/44, unarchived) and gave articles
two crops: `hero_crop`, free-shape between 4:1 and 1:1, for the image above the
body; and `card_crop`, always 16:9, for listing cards, derived from the hero
when not overridden.

Removing the hero removes `hero_crop`'s only two consumers —
`ArticleRenderContent.tsx:98` and `HeroImageUploader` — and with them the
derivation rule, the free-shape cropper mode and the "reset to match hero"
control. What is left is one image and one 16:9 rectangle, which both card
variants already share (`ArticleCard` passes `card_crop` for `lead` and `grid`
alike). The parts of yesterday's work that survive are the ones that matter:
`CroppedImage`, the normalised-rectangle storage model, the fixed-ratio cropper,
and server-side resolution so the preview cannot disagree with the listing.

Other ground this stands on:

- `patch_article` distinguishes "field omitted" from "field set to null" via a
  module-level `UNSET` sentinel and `payload.dict(exclude_unset=True)`.
- `derive_summary` (`services/articles/summary.py`) exists only in Python, on
  purpose. That is why the editor previews a *saved* article.
- Article images are already kept out of the project gallery, cover-image pick
  and 10-image cap, but only by a `source` flag that says nothing about *which*
  article.
- `GradientPlaceholder` is used by nine other surfaces, so it survives this
  change even though article cards stop using it.

## Goals / Non-Goals

**Goals:**

- An article can exist, and publish, with no image at all.
- One image per article, one crop, one framing shared by both card variants.
- The author chooses the image from what is already in their article, without
  re-uploading it.
- Listing settings are a place in the editor, not a modal stack.
- A sensible default that costs no clicks, and an explicit way to refuse it.
- Images are linked to their article in the database, not inferred.

**Non-Goals:**

- Framing images inside the article body. The free-shape cropper would find a
  home there, but it is a separate feature and it is not built on speculation.
- Per-variant framing (a different crop for the lead card). Explicitly rejected
  by the author: one image selection, one rendering.
- Reprocessing or cropped derivative files. Unchanged from
  `article-hero-cropping` — a crop is a stored rectangle applied in CSS.
- Garbage-collecting S3 objects for deleted images. Pre-existing gap, made no
  worse here.

## Decisions

### Three modes, not a nullable id

"Default to the article's first image" and "the author can remove the image"
cannot both live in `listing_image_id = NULL`. If they try, removal does not
stick: the next save re-adopts that image and the card the author deleted comes
back.

```python
class ListingImageMode(models.TextChoices):
    AUTO = "auto", "First image in the body"
    CHOSEN = "chosen", "Author's choice"
    NONE = "none", "No image"
```

| mode | `listing_image` | `listing_crop` | card shows |
|------|-----------------|----------------|------------|
| `auto` (default) | set on save, or null | always null | first upload, 16:9 centred |
| `chosen` | the author's pick | the author's frame | exactly that |
| `none` | null | null | headline, no image |

Every action in the wizard sets `chosen` — including adjusting the crop without
changing the image. Otherwise the next save re-derives the image and swaps it
out from under a rectangle the author just drew. "Remove image" sets `none`.

### `auto` resolves on save, not on read

Resolving in `create_article`/`update_article` means `listing_image_id` is
always populated and a listing card is a plain FK join.

Resolving on read would mean a per-article subquery over `ProjectImage` for
every card in a grid, to compute something that changes only when the author
uploads or deletes an image. Rejected.

The mode field survives the resolution, so the editor can still say "the first
image you uploaded" rather than presenting a choice the author never made.

`auto` sets `listing_crop = None`, and a null crop already renders as 16:9
centred (`CroppedImage`'s existing fallback). There is nothing to derive.

### `auto` means first uploaded, not first in the body

```python
article.images.order_by("created_at").first()
```

`ProjectImage.Meta.ordering` is `["display_order", "created_at"]`, and article
uploads all take `display_order` from the project's non-article image count — so
the default ordering is meaningless among them and the query orders by
`created_at` explicitly.

The alternative was reading the body: parse `![alt](url)`, strip
`S3_PUBLIC_URL_BASE`, look the storage key up. It answers a slightly better
question — "which image leads the article" rather than "which arrived first" —
and the two differ when an author puts an image at the foot of a piece and later
adds one at the top.

Rejected anyway. It is a markdown parser, a URL-to-storage-key mapping and a
lookup, all to improve a default that the author can override in two clicks in
the panel that shows them the result. Nothing in this change parses a body.

The cost is stated in Risks: `auto` can settle on an image the author has since
removed from the body, because deleting an image from the markdown does not
delete the `ProjectImage` row.

### `ProjectImage.article`, a real FK

`ProjectImage` already carries a hard `project` FK, so ownership is settled;
what is being added is "and which article, if any".

```python
article = models.ForeignKey(
    "articles.Article", null=True, blank=True,
    on_delete=models.CASCADE, related_name="images",
)
```

A `GenericForeignKey` was considered for the second owner type that discussions
may one day want. Rejected: it costs referential integrity, `select_related`
and cascade behaviour permanently, starting now, for a case that does not exist.
When discussions need images that is one more nullable FK and one more line in
the resolver — cheaper than the framework tax, and reversible.

The API keeps a polymorphic shape even though storage does not:

```
POST .../images/presign   { source: "article", source_id: "<uuid>", ... }
                                  │
                                  ▼
                          ProjectImage.article_id
```

`ImageSource` moves out of `apps/projects/models.py` into
`api/schemas/project.py`. It no longer describes a column; it selects which
column the request populates.

### `source` is derived, not stored

With a link there is no reason to also keep a flag that can disagree with it.
Five call sites change from `source` to the FK:

| site | before | after |
|------|--------|-------|
| `schemas/project.py:113` | `img.source != ARTICLE` | `img.article_id is None` |
| `services/project/django_impl/query.py:48` | `.exclude(source=ARTICLE)` | `.filter(article__isnull=True)` |
| `routers/my_projects.py:251` | image-cap count | same swap |
| `routers/my_projects.py:324` | never promote to `is_main` | same swap |
| `routers/my_projects.py:410` | main-image promotion | same swap |

`ProjectImageResponse` never exposed `source`, so removing the column changes no
read contract.

### Cascade direction, and why `listing_image` stops being `PROTECT`

`ProjectImage.article` must be `CASCADE`. Under `SET_NULL`, deleting an article
would leave its images with `article_id = NULL` — which, now that `source` is
derived, means they would reappear in the project's gallery and count against
its image cap. An orphan surfacing in the UI is worse than an orphan in S3.

That cascade puts `Article.listing_image` in a cycle: deleting an article
collects its `ProjectImage` rows, and those rows are referenced by the same
article's `listing_image`. Rather than rely on how Django's collector orders a
self-consistent cascade, `listing_image` becomes `on_delete=SET_NULL`.

The trade-off is that deleting an image can silently blank a card. In practice
the only delete path is the wizard's best-effort cleanup of a cancelled upload,
which was never assigned. If a chosen image is deleted, the article keeps
`mode = chosen` with a null image and renders as a text-only card — visible, and
fixable in the same panel.

### Cards without an image

```
  lead                                grid
  ┌────────────────────────────┐      ┌──────────────┐ ┌──────────────┐
  │ CHANNEL · 6 Aug            │      │ CHANNEL·6Aug │ │ ▓▒░ image ░▒▓│
  │                            │      │ Headline     │ ├──────────────┤
  │ A headline with room to    │      │ that gets    │ │ CHANNEL·6Aug │
  │ run to three or four lines │      │ four lines   │ │ Headline two │
  │                            │      │ now          │ │ lines        │
  │ Summary text, more of it   │      │ Summary...   │ │ Summary...   │
  └────────────────────────────┘      └──────────────┘ └──────────────┘
```

No image element and no placeholder — the headline and summary take the space.
Line clamps go from `2 → 4` (grid headline), `3 → 5` (grid summary), `3 → 4`
(lead headline), `2 → 4` (lead summary). Grid rows already stretch to equal
height, so a mixed grid stays aligned without further work.

A bare text block in the **lead** slot is the risk: at full column width it can
read as a card whose image failed to load rather than as a deliberate choice.
This is left to the implementer to resolve against the real rendering — a rule
above the headline, a tinted panel, a larger headline, or a combination. The
requirement is that an imageless lead card must not look broken; the mechanism
is not specified here because it needs to be looked at rather than reasoned
about.

### Listing settings as a tab

```
 ┌────────────────────────────────────────────┐
 │ [ Article title            ] [ Channel ▾ ] │  ← above the tabs; the title
 ├────────────────────────────────────────────┤     is what the card preview
 │  Content  │ Listing settings               │     renders
 ├───────────┴────────────────────────────────┤
 │  Summary  [                            ]   │
 │  Image    [ thumb ]  Change…  Remove       │
 │                                             │
 │  ┌ As lead story │ In the grid ┐            │
 │  │  ┌───────────────────────┐  │            │
 │  │  │      card render      │  │            │
 │  └──┴───────────────────────┴──┘            │
 └────────────────────────────────────────────┘
```

Title and channel stay above the tab strip: they are article identity, the title
appears in the card preview, and an author tuning a headline for the card should
not have to change tabs to do it.

Switching to **Listing settings** saves the draft first. The preview needs
`summary_display`, which only Python can compute, so it must render a saved
article — this is what `handlePreviewClick` already does before opening the
dialog. Two alternatives were considered and rejected: mirroring
`derive_summary` in TypeScript (two implementations of one rule, which
`summary.py` explicitly refuses), and a non-persisting
`POST /articles/{id}/preview-summary` (an endpoint whose only purpose is to
avoid a save the page is entitled to make anyway).

The nested tab pair exists because the dialog stacked both cards and the author
saw the same article twice in one viewport.

### Eager draft creation on `/new`

An upload cannot carry `source_id` for an article that does not exist. Opening
`/projects/<slug>/articles/new` therefore POSTs an empty draft and
`router.replace`s to `/edit/<id>` — the same swap that happens today on first
save, moved earlier.

Guarded by a ref against React StrictMode's double effect in development, which
would otherwise create two drafts per visit.

Abandoned empty drafts are the cost. Mitigated, not eliminated: on unmount, if
the draft is still untouched (no title, no body, no listing image, no uploaded
images), it is deleted best-effort. Anything that survives that is a draft in
the author's own list, invisible to readers, with a delete button next to it.

Rejected alternative: saving lazily on the first image insert. It hides a write
behind an unrelated action and can fail at the worst moment.

### The wizard

```
  ┌─ Choose a listing image ──────────────────────┐
  │  [current]  [body-1]  [body-2]  [body-3]      │   step 1
  │     ✓                                          │
  │  ┌──────────────────┐                          │
  │  │  + Upload new    │                          │
  │  └──────────────────┘                          │
  │                          [Remove image] [Next] │
  └────────────────────────────────────────────────┘
                    ↓  (a fresh upload lands here too)
  ┌─ Frame the card ──────────────────────────────┐
  │        ImageCropper, lockRatio 16:9            │   step 2
  │                              [Back]  [Use it]  │
  └────────────────────────────────────────────────┘
```

Step 2 is `ImageCropper` inside a wizard step, not a nested `ImageCropDialog` —
which is exactly the reuse `article-hero-cropping` designed for.

Step one lists `article.images` — the reverse of the `ProjectImage.article` FK,
carried on `ArticleOut` and prefetched with variants. That is the whole point of
linking at the database level: no endpoint of its own, no markdown parse, and no
dependence on what happens to be saved.

It also removes a special case. An image uploaded through the wizard is never in
the body, so a body-derived list would have had to pin the current selection
separately; an FK-derived list already contains it.

Rules:

- Re-picking the image that is already chosen opens step 2 on its stored crop.
  Picking a different one resets to a centred default — a rectangle drawn on one
  image means nothing on another. Both rules already exist in `handleHeroUpload`
  and `_apply_crop_changes`.
- Only images with recorded dimensions are selectable; without them there is
  nothing to frame.
- Cancelling after a fresh upload deletes the upload, best-effort, as the hero
  dialog does today.

`ArticleOut` grows the list rather than gaining a sibling endpoint. It costs the
article render page a handful of image records it does not use — `listing_image`
already ships with its variants, so this is a difference of degree — and it
saves the editor a second request at the moment the wizard opens.

### What `crop.py` loses

`derive_card_crop`, `resolve_card_crop`, `MIN_RATIO`, `MAX_RATIO` and the
`expected_ratio is None` branch of `validate_crop` all go. Every crop is now
16:9, validated against `CARD_RATIO`. `CropRect`, `parse_crop` and the
overlap/extent checks stay unchanged.

On the API this collapses the `card_crop` / `card_crop_display` pair into a
single stored `listing_crop`. There is nothing left to resolve.

`ImageCropper` loses `minRatio`, `maxRatio`, the edge handles and the
free-shape hint; `lockRatio` becomes required. It is recoverable from git if
body-image framing ever wants it, and an untested code path with no caller rots.

## Risks / Trade-offs

**Deleting the hero deletes work that is one commit old** → Accepted, and
deliberately. `CroppedImage`, the storage model and the fixed-ratio cropper —
the durable parts — all survive. What goes is the free-shape mode, which exists
only to serve a rendering the product no longer wants.

**Abandoned empty drafts from eager creation** → Best-effort delete on unmount
when untouched. Residue is a draft in the author's own list. If it becomes a
nuisance, a management command sweeping empty untitled drafts is a small
follow-up.

**Saving on a tab click surprises the author** → The page is a draft editor and
already auto-creates; a save is not a destructive act here. The tab shows the
existing "Draft saved" confirmation so it is not silent.

**A chosen image deleted underneath an article blanks its card** → The direct
cost of `SET_NULL`, taken to avoid a delete cycle. The card degrades to
text-only rather than erroring, and the panel shows it.

**`auto` picks an image the author did not think of as the lead** → It is the
first image they uploaded to the article, which is a decent guess and a cheap
one, and the panel says which image it is and offers both other modes one click
away.

**`auto` can settle on an image no longer in the article** → Deleting an image
from the markdown does not delete the `ProjectImage` row, so an image the author
inserted, thought better of, and removed can still be the earliest upload and
therefore the card image. It is visible in the panel and one click from being
changed. The body-parsing alternative that would avoid it was rejected above as
too much machinery for a default.

**Two unarchived capabilities contradict this one until reconciled** → Both
edits are tasks in this change, not follow-ups. Skipping them leaves
`add-article-authoring` archiving a hero-is-required rule into `openspec/specs/`
after this ships.

## Migration Plan

Only test data exists, so there is no backfill and no compatibility window. The
migrations are still generated with `makemigrations` rather than hand-edited, so
a local database moves forwards without being rebuilt.

1. `apps/articles` migration: rename `hero_image` → `listing_image`, rename
   `card_crop` → `listing_crop`, drop `hero_crop`, add `listing_image_mode`,
   alter `listing_image` to `SET_NULL`. Answer `makemigrations`' rename prompts
   with *yes* — accepting drop-and-add would discard the columns.
2. `apps/projects` migration: add `article` FK, drop `source`. Depends on the
   articles migration.
3. `make extract-openapi` in `src/django-backend/`.
4. `npm run generate-types` in `src/web-ui/`.
5. Deploy is a single step. The renamed request and response fields are
   breaking, so backend and frontend ship together.

## Open Questions

- The visual treatment of an imageless **lead** card. Deliberately unresolved —
  see Decisions. The implementer decides against the real rendering, and the
  requirement is only that it must not read as a broken card.
- Whether `auto` should fall back to the project's main image when the body has
  no images at all. Currently it does not — no image means no image. Easy to add
  later, and adding it later does not invalidate stored data.
