# 06. Listing tab publishes unsaved edits

**Finding:** I6 (frontend B3) — clicking "Listing settings" calls `draft.save()`, and on a published article that writes half-finished body text straight to the live page.

**Alex:** "Interesting point! I assume fixing this would mean having the idea of an unpublished revision or similar. Quite a big change. We can discuss this but I think if it's as big as i think it is we'll need to push that to follow ups."

**Type:** fix proposal

**Effort:** S for the fix I recommend — about half a day, four frontend files, one backend test, no schema and no OpenAPI change. The draft-revision model you are picturing is genuinely L, but it is not what this finding requires.

## Short answer to the sizing question

No, it is not as big as you think. The premise — that the listing tab needs the body on the server, so avoiding the write needs somewhere else to put the body — is wrong. The tab needs a server round-trip for three *derived* values, and none of them requires the author's unsaved body to be persisted. The write can be reduced to an empty `PATCH` today, with no new concepts.

Draft revisions solve a different problem: "editing a published article should be safe in general, including via the Save button". That is a product feature, not this bug, and it belongs in follow-ups.

## What is actually happening

`ArticleAuthoringPage.tsx:131` (`handleTabClick`):

```ts
setIsSwitchingTab(true);
const saved = await draft.save();
setIsSwitchingTab(false);
if (saved) setTab("listing");
```

`save()` → `snapshotForm()` → `persistDraft()` (`useArticleDraft.ts:259-292`) sends the full payload — `title`, `body`, `channel_id`, `summary`, and the three listing fields — through `api.articles.update`. `patch_article` (`api/routers/articles.py:183`) is the same endpoint for a draft and for a published article; `ArticleState` is not consulted anywhere on that path. `draft.isPublished` only changes a button label (`ArticleAuthoringPage.tsx:182-186`).

So: open a published article, type one character in the body, click the tab, and that character is live.

### What the tab genuinely needs from the server

I traced every value the listing tab renders. `ListingSettingsPanel` receives `article` (last saved) plus `summary` / `crop` / `mode` from the live form, and `listingImage` derived from `article.images`.

| Rendered value | Source | Needs a round-trip? |
|---|---|---|
| Summary textarea value | `form.summary` | No — client state |
| Summary placeholder (`article.summary_display`) | `derive_summary(saved body)`, `api/schemas/article.py:130` | **Yes** — depends on the *saved* body |
| Card summary fallback (`toListItem`, `ArticleCardPreview.tsx:36`) | same `summary_display` | **Yes**, same one |
| Thumbnail + card image | `article.images` lookup | **Yes** — inline uploads never touch draft state (that is finding I4) |
| `auto` listing image | `_apply_listing_image` (`handler.py:267-271`) resolves `auto` → first uploaded article image | **Yes**, and it is settled on *write*, not on read |
| Crop, mode | `form.listing_crop`, `form.listing_image_mode` | No |
| Card title (`toListItem` uses `article.title`) | last save | No — but the component reads the wrong field today |
| Card channel chip (`ArticleCard.tsx:56` uses `article.channel.name`) | last save | No — same |

Three real dependencies, all derived: the summary derived from the saved body, the article's uploaded images, and `auto` resolution. The body itself is needed by exactly one of them, and only so the *fallback* summary is fresh.

The comment at `ArticleAuthoringPage.tsx:127-130` names the summary and stops there. It does not mention `article.images` or `auto`, and it does not mention that the card preview also silently depends on a save for the title and the channel — which is why "just don't save" is not a one-line change either.

### The API already allows a body-less PATCH

`ArticleUpdate` (`api/schemas/article.py:36`) is all-optional, `patch_article:198` reads `payload.dict(exclude_unset=True)` for the two fields where `null` is meaningful, and `update_article` (`handler.py:110-118`) skips `title` / `body` / `summary` when they arrive as `None`. `_apply_listing_image` runs unconditionally, so an *empty* `PATCH {}` still re-resolves `auto` and still returns a fresh `images` list and a fresh `summary_display`. The generated TS type (`api-types.ts:1928`) has every field optional, so `api.articles.update(ref, id, {})` compiles today.

No backend change, no OpenAPI regeneration, no migration.

## Proposed change

A ladder, smallest first.

### Rung 0 — confirm before the implicit save when published (XS, ~15 lines)

`window.confirm("Save your changes to this live article first?")` in `handleTabClick`.

Loses. It puts a modal on a tab click, and the author still cannot see how the card looks without pushing a half-finished edit live. It converts a silent problem into a loud one without removing it.

### Rung 1 — the tab refreshes instead of saving (S, ~40 lines + tests) — **recommended**

Replace `draft.save()` in `handleTabClick` with a `draft.refreshListing()` that sends nothing, and move the three preview fields that were riding on the save into props.

`useArticleDraft.ts`, alongside `save`:

```ts
// Opening the listing tab needs three things only the server holds: the
// summary derived from the SAVED body, this article's uploads (inline
// uploads never reach draft state), and `auto` resolved to an image —
// which is settled on write, not on read. An empty PATCH gets all three
// and persists nothing the author has typed, so opening a tab can never
// push an edit onto a live article.
const refreshListing = useCallback(async (): Promise<Article | null> => {
  if (!article) return null;
  setError("");
  try {
    const updated = await api.articles.update(projectRef, article.id, {});
    setArticle(updated);
    // Only while the form is still in `auto`: a choice made in the wizard
    // since the last save must not be reverted by a resolution the server
    // computed without knowing about it.
    setForm((prev) =>
      prev && prev.listing_image_mode === "auto"
        ? {
            ...prev,
            listing_image_id: updated.listing_image_id,
            listing_crop: updated.listing_crop,
          }
        : prev,
    );
    return updated;
  } catch (err) {
    setError(describeApiError(err, "Couldn't open listing settings"));
    return null;
  }
}, [article, projectRef]);
```

(`describeApiError` is document 15. Until that lands, keep the existing `err instanceof Error ? err.message : …` shape.)

`ArticleAuthoringPage.tsx:137-140`:

```diff
   setIsSwitchingTab(true);
-  const saved = await draft.save();
+  const refreshed = await draft.refreshListing();
   setIsSwitchingTab(false);
-  if (saved) setTab("listing");
+  if (refreshed) setTab("listing");
```

and the comment at `:127-130` gets rewritten to say what the round-trip is for.

Then the preview stops reading stale fields. `toListItem` (`ArticleCardPreview.tsx:26`) is already at four positional arguments; convert it to an overrides object and add `title` and `channelName`:

```ts
interface Overrides {
  title?: string;
  channelName?: string;
  summary?: string;
  imageUrl?: string | null;
  crop?: CropRect | null;
}
```

`ListingSettingsPanel` takes `title` and `channelName` and passes them down; `ArticleAuthoringPage` supplies `form.title` and the channel matching `form.channel_id` from `draft.channels`.

Net effect: everything the author can edit is previewed live from form state; the one thing that lags is the *derived* summary, and only when the author has left the summary field empty. The Save button sits three centimetres away and is honestly labelled.

### Rung 1′ — branch on `isPublished` (S, smaller still)

`if (draft.isPublished) refreshListing() else save()`. Preserves today's behaviour exactly for drafts, so no preview regression in the common case.

Loses, narrowly. It adds a second code path to a UI whose whole point is that drafts and published articles edit identically, and it keeps a tab click writing to the database in the case that is harder to test. The preview regression it avoids is one save's worth of staleness on a fallback string. Not worth the branch — but if you disagree, this is a legitimate variant of the same rung.

### Rung 2 — port `derive_summary` to TypeScript (M, 1–2 days)

Removes the last round-trip dependency, so the tab switch could be pure client state (with `auto` resolved client-side as `images[0]`, which is exactly what `handler.py:270` does).

Cost: `summary.py` is 48 lines and six regexes — a mechanical port. The expensive part is keeping the two honest. `markdown-parity.test.tsx` is **not** the precedent: it compares two TypeScript pipelines inside one vitest process, so a drift shows up as a failing assertion in the same run. A Python/TypeScript pair cannot do that. It needs a shared fixture — `services/articles/summary_cases.json` with the eleven cases now hard-coded in `services/articles/test_summary.py`, read by both pytest and vitest — plus a rule that new cases go in the fixture. That is a permanent tax on a function whose docstring currently says, in as many words, "Lives only here — a second implementation in TypeScript would drift".

Loses now: it buys a fresher preview of a fallback string. Take it later if authors actually complain that the preview lags.

### Rung 3 — draft revisions (L, 1–2 weeks, follow-up)

For completeness, since it is what you asked about. Concretely it means:

- **Schema.** Either shadow columns on `Article` (`draft_title`, `draft_body`, `draft_summary`, `draft_listing_*`) or an `ArticleRevision` table. Shadow columns are the cheap half; a revision table is the honest one.
- **Publish semantics.** `publish()` (`handler.py:139`) is currently a one-way `DRAFT → PUBLISHED` transition that assigns a slug and fires notifications. It becomes "promote the working revision", i.e. re-entrant. That forces two decisions: `published_at` must not move on a re-publish, and `create_notifications_for_article` (`:165`) must not re-fire — there is no "already notified" guard today, and `_is_backdated` will not save you.
- **Images.** `ProjectImage.article` is per-article, not per-revision. An image inserted into an unpublished revision is already stored, already counts against the 30-image cap, and — because `_apply_listing_image` resolves `auto` from `article.images.uploaded()` — can already become the live card's image. So either image rows get revision scoping, or `auto` has to resolve against the live revision's body. Neither is small.
- **API.** PATCH writes the working revision; a new endpoint discards it; `ArticleOut` grows a working/live distinction. OpenAPI regen, type regen, and `_get_article`'s prefetch chain changes.
- **UI.** An "unpublished changes" banner, a discard action, a preview toggle between "what readers see" and "what you have written", and the read page must keep serving the live revision to everyone — including the author, who currently sees drafts via `_can_view_draft`.
- **Migration.** Backfill a working revision per published article, or create lazily on first edit.

This is real work and it is a feature: "edit a live article without publishing as you go". It has nothing to do with a tab click writing to the database.

**Ship rung 1 in this change.** Push rung 3 to `FOLLOW_UPS.md`.

## Tests

Frontend, `use-article-draft.test.tsx` — new `describe("opening the listing tab")`:

- sends an empty patch rather than the article — assert `articles.update` was called with `{}`
- does not send a body the author has typed but not saved — set the body through `handleBodyChange`, call `refreshListing`, assert the payload has no `body` key
- adopts the image the server resolved for `auto`
- leaves a wizard choice alone when the mode is `chosen` (this is also half of B4)
- keeps the tab shut and reports the error when the refresh fails

Frontend, `article-card-preview.test.tsx` — extend the existing `describe("toListItem")`:

- prefers the unsaved title over the saved one
- prefers the unsaved channel name over the saved one

Backend, `api/routers/test_articles.py`, next to `test_auto_adopts_the_first_upload_on_save:492`:

- `test_an_empty_patch_resolves_auto_without_touching_the_body` — PATCH `{}`, assert `listing_image_id` is the first upload and `title`/`body` are unchanged. This pins the contract the frontend now depends on; without it, adding a required field to `ArticleUpdate` would break the listing tab silently.

Playwright: the frontend review notes `handleTabClick` has no coverage at all. One spec — open a published article, type in the body, switch to Listing settings, reload, assert the body is the published one — would be the regression guard that matters. Optional; the vitest cases catch the same thing more cheaply.

## Risks and what this does not cover

- **`auto` re-resolution is still a write.** An empty PATCH will change `listing_image` on a published article if the author has inline-uploaded an image since the last save, because the upload completes server-side immediately. It is derived state, it is idempotent with what any save would do, and it only fires for authors who uploaded to this article — but it is not literally zero-write. If that is unacceptable, resolve `auto` client-side as `images[0]` and use a plain `GET` instead; the cost is one duplicated rule.
- **The Save button is unchanged.** Pressing "Save" on a published article still writes live, with no confirmation. That is a button labelled Save, so it is honest; making it *safe* is rung 3.
- **The preview's derived summary lags one save.** Accepted trade, see rung 2.
- **`_get_article` (`handler.py:353`) does not prefetch `images__variants`**, so the extra PATCH pays the same ~13 avoidable queries the review already flags as a separate minor. Rung 1 does not make it worse (it replaces a save with a refresh, not adds one), but it does make the query cost more visible.
- **Findings I4 and B4 are untouched.** I4 (leaving mid-upload deletes the draft) shares a root cause — inline uploads never reach draft state — and rung 1 does not fix it. The `mode === "auto"` guard above happens to close the tab-switch half of B4; the Save-button half remains.
