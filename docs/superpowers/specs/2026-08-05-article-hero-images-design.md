# Article Hero Images — Design

Date: 2026-08-05
Status: superseded (2026-08-06) by the `article-listing-image` capability —
articles no longer have a hero image, and none is required to publish. Kept as
a record of what was decided at the time.

## Summary

Two things go wrong with article hero images today. Removing one and saving does
nothing — the API cannot express removal. And the article listing renders a
deliberately wide hero as a 96px square, so choosing a good image is wasted
effort.

This change makes removal work, gives articles an optional summary line with a
derived fallback, and rebuilds the project's Articles tab as a lead story
followed by a two-column card grid. A card preview dialog in the editor is where
the summary is written.

Addresses these items in `openspec/changes/archive/2026-08-07-add-article-authoring/feedback.md`:

- "Hero image doesn't get removed - click remove and save and it remains"
- "If we're going to select large wide images to represent the article, we
  should have the list of displaying articles be better at rendering those
  images. Right now it shows it as truncated icon."

Backend and frontend. Needs a migration and an OpenAPI + type regeneration.

## Hero removal cannot be expressed

`ArticleUpdate.hero_image_id` is `UUID | None = None`
(`api/schemas/article.py:20`), so "cleared" and "not sent" arrive as the same
value. `update_article` then reads `None` as "leave alone":

```python
# services/articles/django_impl/handler.py:105
if hero_image_id is not None:
    hero_image = self._resolve_hero_image(hero_image_id, article.project_id)
    if hero_image and hero_image.pk != article.hero_image_id:
        ...
```

The frontend is doing the right thing — `useArticleDraft.ts:161` sends
`hero_image_id: current.hero_image_id ?? null` on every save. The null lands and
is discarded.

### Fix: sentinel plus `exclude_unset`

`api/routers/auth.py:193` already uses `payload.dict(exclude_unset=True)`; this
follows it.

- `services/articles/handler_interface.py` gains a runtime module-level
  sentinel:

  ```python
  class UnsetType:
      """Distinguishes 'field omitted' from 'field explicitly set to null'."""

  UNSET = UnsetType()
  ```

  It must sit outside the `TYPE_CHECKING` block — the file has
  `from __future__ import annotations`, but the value is needed at runtime.

- `update_article`'s `hero_image_id` becomes
  `UUID | None | UnsetType = UNSET`, in both the interface and
  `django_impl/handler.py`.

- `patch_article` (`api/routers/articles.py:166`) passes the field only when the
  client sent the key:

  ```python
  provided = payload.dict(exclude_unset=True)
  ...
  hero_image_id=provided.get("hero_image_id", UNSET),
  ```

  `.dict()` defaults to python mode, so the value is still a `UUID`.

- The handler branch becomes `if hero_image_id is not UNSET:`. `None` now
  clears. The `if hero_image and …` guard collapses to a plain inequality —
  `_resolve_hero_image` (`handler.py:247`) raises
  `HeroImageOnWrongProjectError` for an unknown id rather than returning `None`,
  so the truthiness check only ever caught the null case, which is the bug.

Only `hero_image_id` gets this. `title`, `body` and `channel_id` have no
ambiguity — their cleared value is `""`, not null — and widening them is churn.

### Published articles keep their hero

`publish()` refuses an article with no hero (`handler.py:132`). Once removal
works, that becomes a gate you can walk back through.

New `PublishedArticleNeedsHeroImageError` in
`services/articles/exceptions.py`. `update_article` raises it when the resolved
hero would become `None` on an article in `PUBLISHED` state; `patch_article`
maps it to 422 with "Published articles need a hero image — replace it rather
than removing it."

The editor disables Save and says so inline while a published article has no
hero, so the author finds out before clicking. Replacing an image is unaffected:
upload the new one, then save.

## Summary field

Optional, stored, with a live fallback.

- `Article.summary = models.CharField(max_length=300, blank=True, default="")`.
  Migration required.
- New `services/articles/summary.py`:

  ```python
  def derive_summary(body: str, limit: int = 200) -> str: ...
  ```

  Drops fenced code, images, headings, blockquote and list markers; unwraps link
  and emphasis syntax; takes the first non-empty paragraph; collapses
  whitespace; truncates on a word boundary with an ellipsis. Returns `""` for an
  empty body. The 200 default is shorter than the field's 300 on purpose — a
  derived excerpt should be a glance, an authored one has room to be a hook.
- `ArticleUpdate.summary: str | None = None`. `""` clears the override and
  returns the article to the fallback — no ambiguity, so no sentinel here.
  `ArticleCreate` is left alone; the summary is only reachable after a first
  save.
- `ArticleListItem.summary: str` resolves to
  `article.summary or derive_summary(article.body)`.
- `ArticleOut` carries both: `summary` (the stored override, so the editor knows
  whether one exists) and `summary_display` (resolved, so the preview shows what
  a listing will).

Resolving at read time rather than freezing a value means rewriting the opening
paragraph updates the card. A stored override always wins, and a
model-written summary later slots in as another stored value overriding the
same way.

**Derivation lives in Python only.** A second TypeScript implementation would
drift from it. That constrains the preview dialog — see below.

## Listing

`ArticlesList.tsx` is the Articles tab on the project page
(`ProjectDetailContent.tsx:226`). Today each row is a `w-24 h-24` `object-cover`
crop (`ArticlesList.tsx:83`), so a 1600×900 hero becomes a centre-cropped stamp.

### `ArticleHeroImage`

New `src/web-ui/src/components/ArticleHeroImage.tsx` — one definition of how an
article hero is framed:

```
ArticleHeroImage({ src, alt, articleId, priority })
```

`aspect-[16/9]` with `object-cover`, `GradientPlaceholder` keyed on `articleId`
when `src` is absent, `loading` driven by `priority`, `decoding="async"`.

The aspect ratio is the actual fix: it crops to a wide band instead of
squashing, so a wide upload lands as-is and a portrait upload gives a centre
band rather than dominating the row.

Used by three call sites, so a card and the article it links to agree about the
same image:

- `ArticleCard`, both variants.
- `ArticleRenderContent.tsx:103`, replacing `w-full h-auto object-cover
  max-h-96` — which crops to whatever `100% × 384px` is at the current viewport,
  so its framing shifts with screen width and never matches the card's.
- `MyProjectArticles.tsx:102`, replacing `w-12 h-12` with `w-20` at 16:9. An
  author picking a wide image should not see it as a square in their own
  management list.

### `ArticleCard`

New `src/web-ui/src/components/ArticleCard.tsx` — in `components/` rather than
page-local because a feed will use it.

```
ArticleCard({ article: ArticleListItem, href: string, variant: "lead" | "grid" })
```

`href` is a prop rather than derived from a project slug: a cross-project feed
builds its links differently.

Both variants are the same stack — hero, channel eyebrow · date, headline,
summary — differing in scale:

| | `lead` | `grid` |
|---|---|---|
| hero | full card width, `priority` | column width, lazy |
| headline | `text-2xl font-semibold`, `line-clamp-3` | `text-base font-semibold`, `line-clamp-2` |
| summary | `text-sm`, `line-clamp-2` | `text-sm`, `line-clamp-3` |

Card chrome keeps the existing `rounded-lg border border-border bg-white
hover:border-accent/50`.

No hero should not occur on a public listing once the invariant above holds, but
the component stays total via `ArticleHeroImage`'s placeholder.

### `ArticlesList`

First article renders as `lead`; the rest go into `grid gap-5 sm:grid-cols-2`.
Sorting and filtering are unchanged (published, has a slug, newest first).
Skeletons change shape to match.

Known rough edge, accepted: with exactly two articles you get a full-width lead
and one half-width card with a gap beside it.

`MyProjectArticles` keeps its compact row layout otherwise — it is a management
list with draft/published badges linking to the editor, not a reader surface.

### Image weight

`docs/image-performance-analysis.md` records that only originals are stored — no
size variants — and these heroes are served as raw `<img>` at full resolution.
Today's 96px square wastes nearly all of it; a 16:9 lead at least uses the
pixels, but a listing of ten articles pulls ten full-size originals.

Mitigation here is limited to `loading="lazy"` on grid cards, eager on the lead,
and `decoding="async"`. The real fix is the upload-time variant generation that
document already recommends. Out of scope.

## Card preview dialog

`ArticleCardPreviewDialog` in `src/web-ui/src/app/projects/[slug]/articles/`,
opened from a "Preview card" button beside Save/Publish in
`ArticleAuthoringPage`. Uses the house `components/Dialog.tsx` — the native
`<dialog>` route established by
[the image-insert change](2026-08-05-article-image-insert-design.md).

**Opening it saves the draft first**, reusing `persistDraft` in
`useArticleDraft.ts`, then renders from the returned `ArticleOut`. This follows
from derivation living only in Python: the panel cannot truthfully preview
unsaved editor state, and the alternative is a TypeScript `derive_summary` that
drifts. If the save fails, the existing error surfaces and the dialog does not
open.

Contents:

- Both variants rendered from the saved article — `lead` at full dialog width,
  `grid` beneath at column width — so the author sees both framings their image
  will get.
- A summary textarea: value `article.summary`, `placeholder`
  `article.summary_display`, helper text "Leave empty to use the start of the
  article", and a counter against the 300 cap.
- Typing updates the preview live. Saving PATCHes `{ summary }`; clearing
  PATCHes `{ summary: "" }`, and the response's refreshed `summary_display`
  flows back into the placeholder and the card.

Split as `ArticleCardPreview` (presentational: article in, summary change out)
inside a thin dialog shell, so a later full-article preview page can host the
same component without unpicking a dialog.

## Testing

Backend (`make test` from `src/django-backend/`):

- `services/articles/django_impl/test_handler.py` — omitted `hero_image_id`
  keeps the hero; explicit `None` clears it on a draft; explicit `None` on a
  published article raises `PublishedArticleNeedsHeroImageError`.
- `api/routers/test_articles.py` — `PATCH {"title": …}` leaves the hero alone;
  `PATCH {"hero_image_id": null}` clears it; the same on a published article is
  422.
- New `services/articles/test_summary.py` — `derive_summary` drops a leading
  heading or image, unwraps links and emphasis, truncates on a word boundary,
  survives a body opening with a code fence, returns `""` for an empty body.
- `ArticleListItem.summary` returns the override when set and the derived text
  when not.

Frontend (vitest, from `src/web-ui/`):

- `ArticleCard` renders both variants and falls back to `GradientPlaceholder`
  with no hero.
- `ArticleCardPreview` shows the derived text as placeholder, sends an override
  on type, sends `""` on clear.

E2E (`src/web-ui/e2e/`): the regression actually hit — upload a hero, save,
remove it, save, reload the edit page, assert it is gone. Runs serially and
deletes its uploads; `/api/auth/login` is rate limited to 5/min per IP
(`api/routers/auth.py:106`) and projects cap at 10 images.

## Mechanical steps this forces

- Migration for `Article.summary`.
- `make extract-openapi` in `src/django-backend/`, then `npm run generate-types`
  in `src/web-ui/` — `ArticleUpdate`, `ArticleOut` and `ArticleListItem` all
  change shape.

## Out of scope

- The notification dock and article digest (`api/schemas/follow.py`) carry their
  own hero image fields and keep their small square icons. A 16:9 crop in a
  notification row would be wrong.
- A standfirst on the article page itself. The summary exists for listings and
  the preview panel; on an article whose summary is the derived fallback, a
  standfirst would repeat the sentence immediately below it.
- Upload-time image variant generation.
- The remaining `feedback.md` items: the preview button, edit-from-view-page,
  and the project page tab default.
