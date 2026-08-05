## Context

Hero framing is currently implicit. `ArticleHeroImage` centre-crops to 16:9 and
is used by the article page, the lead card and the grid card;
`HeroImageUploader.tsx:41` does something else again — `w-full max-h-80
object-cover`, a fixed pixel ceiling against a fluid width, so the editor's
framing changes as the window resizes and never matches the article page.

The pieces this builds on already exist:

- Image variants (`thumb` 384w / `medium` 768w / `large` 1536w) are generated on
  upload and reachable via `pickVariant`. They are width-based resizes, so they
  preserve the source aspect.
- `ProjectImage` records `width` and `height` (both nullable).
- Article images are already separated from the project gallery
  (`ImageSource`), so a hero is not shared with anything else on the project.
- `patch_article` already distinguishes "field omitted" from "field set to null"
  via a module-level `UNSET` sentinel plus `payload.dict(exclude_unset=True)`.
- `ArticleCardPreviewDialog` already exists as the surface where an author looks
  at their cards.

## Goals / Non-Goals

**Goals:**

- One hero rendering path shared by the editor and the article page, so what the
  author frames cannot diverge from what a reader sees.
- A crop picker that is reusable outside articles, and that shows the author
  their whole image rather than only the part that survives.
- Author-chosen hero aspect ratio, frozen with the article and honoured at every
  viewport.
- Uniform 16:9 listing cards, framed automatically from the hero and overridable.
- No image reprocessing: cropping is a stored rectangle, applied at render.

**Non-Goals:**

- Server-side cropped derivatives. Considered and rejected — see Decisions.
- Per-viewport art direction (a different crop on phones). It contradicts the
  frozen-ratio decision.
- Cropping project banners, gallery images or in-body article images.
- Reducing hero download weight. CSS cropping makes it marginally worse, and the
  real fix is elsewhere (see `docs/image-performance-analysis.md`).

## Decisions

### Store a normalised rectangle, crop with CSS

Two nullable JSON columns on `Article`:

```python
hero_crop = models.JSONField(null=True, blank=True)
card_crop = models.JSONField(null=True, blank=True)
```

Shape: `{"x": float, "y": float, "w": float, "h": float, "ratio": float}`, with
`x/y/w/h` normalised against the *source* image and `ratio` the rendered aspect
as a decimal (`34/12 → 2.8333`).

Values outside 0–1 are legal and meaningful: the author can zoom out until the
crop box is larger than the image, and what the box takes from beyond the edge
renders as a shared background colour (white). The only geometric constraints
are that the crop still overlaps the image somewhere and is no more than six
times its size.

`ratio` is derivable from `w·W : h·H`, but it is stored anyway for two reasons:
`ArticleListItem` carries only a hero URL, not the source pixel dimensions, so a
card would otherwise need them shipped alongside; and the renderer must know the
ratio *before* the image loads to reserve the box and avoid layout shift.

Alternative considered: generate a cropped derivative on save. Rejected — every
re-crop means another processing pass, another stored file, an orphan, a stale
CDN entry and a "processing…" state in the dialog. Cropping is editorial and gets
fiddled with; it should be free.

Crops live on `Article`, not `ProjectImage`. The card crop is a listing concern
the image knows nothing about, and keeping `ProjectImage` free of
article-specific framing avoids the field being meaningless for banners and
gallery images.

### `CroppedImage` primitive

New `src/web-ui/src/components/CroppedImage.tsx`. An `aspect-ratio` box with the
image absolutely positioned and scaled by percentage:

```tsx
<div style={{ aspectRatio: String(crop.ratio) }} className="relative overflow-hidden">
  <img
    src={src}
    style={{
      position: "absolute",
      width: `${100 / crop.w}%`,
      height: `${100 / crop.h}%`,
      left: `${(-crop.x / crop.w) * 100}%`,
      top: `${(-crop.y / crop.h) * 100}%`,
      maxWidth: "none",
    }}
  />
</div>
```

`maxWidth: "none"` is load-bearing: a global `img { max-width: 100% }` reset
would silently cap the scaled image and shift the crop.

The same arithmetic covers a crop that runs past the image: `w > 1` makes the
image narrower than its box and a negative `x` pushes it inwards, leaving
`CROP_BACKGROUND` showing at the edges. No special case.

`crop == null` falls through to the current path — 16:9 with `object-cover` —
which is why pre-existing articles need no backfill.

`ArticleHeroImage` becomes a thin wrapper over this that takes `crop`, and
`ArticleCard` uses it with the resolved card crop. `HeroImageUploader`'s preview
switches to `ArticleHeroImage`, which is the whole of the a≠b fix.

### `ImageCropper`, and a dialog around it

New `src/web-ui/src/components/ImageCropper.tsx`. It knows nothing about
articles — it takes an image and a rectangle and hands back a rectangle — so the
next surface that needs cropping drops it into a panel or a page rather than
inheriting a modal. `ImageCropDialog` is a thin wrapper that supplies the house
`components/Dialog.tsx` and the confirm/cancel buttons.

```
ImageCropper({ src, naturalWidth, naturalHeight, value, onChange,
               lockRatio?, minRatio?, maxRatio?, minSourceWidth?, previewLabel? })
```

The model is *whole image, box on top* rather than *box only*:

- The stage shows the entire image. A dashed box is drawn over it at the crop,
  with a light scrim outside — light on purpose, since the point of showing the
  whole image is that the author can see what they are leaving out.
- The box keeps a fixed size on screen. **Zoom scales the image beneath it**, so
  zooming in narrows the focus. Zoom is exactly `1 / crop.w`, and the slider's
  track is logarithmic — on a linear 0.25–8 track, 1× sits at 10% and the whole
  useful range is crushed against the left end.
- Zooming out below 1 leaves the box larger than the image. That is allowed:
  the surround is `CROP_BACKGROUND`, and the stage paints the same colour
  behind the box so it matches what the result will be.
- Dragging pans; dragging the box's top or bottom edge changes its shape, about
  the box's centre. Zoom and resize both preserve the crop's centre, so the
  subject does not drift out of frame while adjusting.
- A live preview renders `CroppedImage` with the working crop, so the author
  sees the actual output rather than inferring it.
- The ratio readout searches denominators for the smallest whole-number pair
  that matches. Reducing the rounded pixel counts instead gives 1125:633 for a
  16:9 box on a 4000×2000 source, which tells the author nothing.
- Under `minSourceWidth` (768) source pixels across the box, an inline warning
  appears. It never blocks — the author may know the image is decorative.

`lockRatio: 16/9` removes the edge handles and fixes the shape, leaving zoom and
pan. That is the entire difference between the hero cropper and the card
cropper, so there is one component rather than two that drift. A fixed-shape
crop is exactly where zooming out past the image edge earns its keep: a portrait
photo in a 16:9 card is better shown whole with bands than cropped to a sliver.

State is held in the same normalised source coordinates that get stored, so
confirming is a pass-through with no conversion step to get wrong.

On small viewports the dialog goes full-screen, and the stage is the only part
that scrolls so the buttons stay reachable however tall the box gets.

### Upload flow

Today `ArticleAuthoringPage.tsx:48` wires `onUploadComplete` straight to
`draft.handleHeroUpload`. It now opens the crop dialog instead:

- **Confirm** → `handleHeroUpload(image, crop)` sets both the hero and its crop.
- **Cancel on a first upload** → the hero is not set and the uploaded image is
  deleted, best-effort. Article-sourced images are excluded from the project
  gallery, so a failed delete leaves an invisible orphan rather than a visible
  one.
- **Cancel when re-framing** → nothing changes.

Clearing the hero clears both crops. Otherwise the next upload inherits a
rectangle chosen for a different image.

### API surface

`CropRect` schema in `api/schemas/article.py`, used on both directions.

Writes go through the existing sentinel machinery, because `null` is meaningful
for both fields — it clears the hero framing, or drops the card override back to
derived:

```python
hero_crop: CropRect | None = None
card_crop: CropRect | None = None
```

with `patch_article` reading them out of `payload.dict(exclude_unset=True)` and
passing `UNSET` when absent, exactly as `hero_image_id` already does.

Reads mirror the `summary` / `summary_display` split:

- `ArticleOut.hero_crop` — stored.
- `ArticleOut.card_crop` — the stored override, so the editor knows whether one
  exists and can show "Reset to match hero".
- `ArticleOut.card_crop_display` — resolved.
- `ArticleListItem.card_crop` — resolved. Listing cards never need the hero crop.

### Derivation lives in Python only

`services/articles/crop.py`:

```python
def derive_card_crop(hero: CropRect, width: int, height: int) -> CropRect | None:
    """The 16:9 rect sharing the hero's centre, clamped inside the image."""
```

Normalised height for 16:9 is `h = w · W · 9 / (16 · H)`, and `x`/`y` keep the
hero's centre. Nothing is clamped: sliding the rect to fit would move the card
away from the subject the author framed, whereas letting it overhang shows the
same subject with background top and bottom — the honest answer, and the one the
cropper itself would have given.

Returns `None` when the image has no recorded `width`/`height` — nullable on
`ProjectImage` — and the renderer falls back to CSS centre-cropping, which is
what those images get today anyway.

This resolves server-side for the same reason `summary` does: a second
TypeScript implementation would drift, and the difference would show as a card
that disagrees with itself between the preview dialog and the live listing.

### Validation

Because a crop may legally run past the image, the geometric checks are about
overlap rather than containment: `w > 0`, `h > 0`, `w ≤ 6`, `h ≤ 6`, and the
rect must intersect the image at all. Free-shape crops need `1 ≤ ratio ≤ 4`; a
card crop must be 16:9 within tolerance. Where the source records pixel
dimensions, `ratio` is checked against `w·W / (h·H)` within 1% — enough to catch
a client computing it wrongly, loose enough to survive float round-tripping.
Failures are 422.

## Risks / Trade-offs

**The browser downloads pixels it then hides** → Accepted, and it is the direct
cost of the no-reprocessing decision. A 4× zoom uses about 1/16 of the fetched
image. Heroes already serve the `large` variant rather than the original, which
caps the damage; genuine improvement needs the work in
`docs/image-performance-analysis.md`, which is out of scope here.

**A global `max-width: 100%` on images breaks the scaled `<img>`** → `maxWidth:
"none"` set inline on the element, and a component test asserting the computed
width, so a future CSS reset cannot regress it silently.

**Stored `ratio` drifting from the rectangle** → Server-side cross-check against
the source dimensions on write, where they are known.

**Cancelling the crop dialog orphans an uploaded image** → Best-effort delete on
cancel. The orphan is invisible either way, since article images are excluded
from the project gallery.

**Touch interaction is fiddlier than mouse** → Pointer events rather than mouse
events, full-screen dialog under `sm`, and generous handle hit areas. Worth
verifying on a real device before this ships.

**Existing published articles look unchanged, so nobody re-frames them** →
Intended. The old rendering stays valid, and an author who cares can open the
editor and set a crop.

## Migration Plan

1. Two nullable columns, additive. No backfill: `null` is a meaningful value
   meaning "the old 16:9 centre crop".
2. Deploy backend first. The new response fields are additive and the old
   frontend ignores them; the new request fields are optional.
3. Deploy frontend.
4. Rollback is dropping back to the previous frontend — the columns are then
   simply unread. The migration itself does not need reverting.

Mechanical, in order: migration → `make extract-openapi` in
`src/django-backend/` → `npm run generate-types` in `src/web-ui/`.

## Open Questions

None blocking. Two things deliberately parked:

- Whether the hero ratio bounds (4:1 to 1:1) are right in practice. They are a
  guess; widen them if authors complain, since loosening a clamp does not
  invalidate stored data.
- Whether the card should eventually offer more than one shape (e.g. a portrait
  variant for a future feed). The stored-rectangle approach extends to an
  additional named crop without reprocessing, so this is not a door being shut.
