# Front-end review — article authoring, listing images, notifications

Scope: `src/web-ui` on this branch vs `main` (~70 files, ~9.9k lines added). Backend and
Terraform were only consulted where the frontend contract depends on them.

Verified before reviewing:

- `npx tsc --noEmit` — clean.
- `npm run lint` — clean.
- `npx vitest run` — 126 tests, 9 files, all pass.
- `make extract-openapi` re-run: `backend-openapi.json` is byte-identical to the committed
  one, so the generated contract is current.

## Summary

The structure is better than most of what lands here. `useArticleDraft` pulls persistence
out of the page component; `CroppedImage` / `ImageCropper` are genuinely domain-free and
take a rectangle and hand one back; `lib/uploadImage.ts` gives the multi-file hook and the
one-shot inline-image path a single implementation; the sub-components under
`articles/` are small and each does one thing. The comments explain *why* rather than
restating the code, and the vitest suites test behaviour rather than implementation.

What follows is what I would hold the merge on. Two of the blockers are user-visible
today; the rest is drift that will cost later.

---

## Blockers

### 1. Any load failure on the authoring page renders a blank screen

`src/web-ui/src/app/projects/[slug]/articles/ArticleAuthoringPage.tsx:91`

```tsx
if (!draft.form || !draft.article) return null;
```

This guard sits *above* every error affordance. `useArticleDraft` sets `error` and
`isLoading = false` on a failed load
(`useArticleDraft.ts:124-128`) but leaves `form` null forever, so the component returns
`null` and the user gets an empty page under the nav bar. `draft.error` is only rendered at
`ArticleAuthoringPage.tsx:137`, which is unreachable in that state.

Concrete path, no exotic conditions needed:

1. Open `/projects/<slug>/articles/new`. A draft is created and the URL swaps to
   `/edit/<id>`.
2. Type nothing and navigate away. The untouched-draft sweep
   (`useArticleDraft.ts:146-154`) deletes it.
3. Press Back. `api.articles.get` 404s. Blank page, no message, no way forward.

A 403 (contributor without `full_edit` who reaches the URL) and a transient network failure
land in the same place.

Fix: render an error state before the null guard — the "Not allowed" block at
`ArticleAuthoringPage.tsx:72-89` is the right shape to copy.

### 2. An image uploaded inside the listing wizard vanishes from the panel until the next save

`src/web-ui/src/app/projects/[slug]/articles/useArticleDraft.ts:307-315`

`images` and `listingImage` are both derived from `article.images`:

```ts
images: article?.images ?? [],
listingImage:
  article?.images.find((image) => image.id === form?.listing_image_id) ??
  (form?.listing_image_id && form.listing_image_id === article?.listing_image_id
    ? article.listing_image
    : null),
```

The wizard's upload path never writes the new image into `article`.
`ListingImageDialog` holds it in local `pendingUpload` state
(`ListingImageDialog.tsx:54`), hands it to `onConfirm`, and unmounts.
`chooseListingImage` sets `form.listing_image_id` to the new id
(`useArticleDraft.ts:176-190`) but nothing calls `setArticle` — which is exported at
`useArticleDraft.ts:302` and, by grep, **used nowhere**. That dangling export is the tell.

So after "Use it" on a fresh upload:

- `listingImage` resolves to `null` → `ListingSettingsPanel` shows the "No image"
  placeholder while the mode label next to it reads "Your choice."
  (`ListingSettingsPanel.tsx:75-96`).
- The card preview below loses its image (`imageUrl` is null).
- The button reverts to "Choose an image…".
- Reopening the wizard doesn't list the upload either, because `images` is still stale.

Hitting Save repairs it, because `persistDraft` calls `setArticle(updated)` and the response
carries `images`. But between confirm and save the UI actively contradicts itself, on the one
screen whose entire job is showing the author what they picked.

The e2e never catches this: `chooseListingImage` in
`e2e/article-listing-image.spec.ts:118` always runs after `saveDraft`, so it only ever
selects images that are already on `article.images`.

Fix: give the hook an `adoptImage(image)` that merges into `article.images`, and have
`chooseListingImage` call it — or drop `setArticle` from the return and thread the image
through explicitly. Either way, delete the unused `setArticle` export.

---

## Important

### 3. `useArticleDraft` has no unit tests

It is 333 lines and holds every non-trivial decision in the feature: eager draft creation on
`/new`, the StrictMode double-create guard, the URL swap, the untouched-draft sweep, the
body-ref snapshot, save/publish/delete, and the `listingImage` derivation that is broken in
finding 2. Everything around it is well covered — `ImageCropper` (13), `ArticleCard` (14),
`ListingImageDialog` (10), markdown parity (18) — which makes the gap conspicuous rather
than excusable. The bug above is exactly the kind a hook test would have caught in one
assertion.

### 4. `ArticlesList` client-fetches on a page that already server-renders, and the server fetcher built for it is dead

`src/web-ui/src/app/projects/[slug]/ArticlesList.tsx:16-43` fetches, filters to published,
and sorts in a `useEffect`. Meanwhile `src/web-ui/src/lib/api/server.ts:77`:

```ts
export async function fetchProjectArticles(projectSlug: string): Promise<ArticleListItem[]>
```

is added in this branch and referenced by nothing (grep confirms). The server path was built
and abandoned.

Consequences: the article listing is absent from the SSR HTML, so it is invisible to crawlers
and to a no-JS load; the reader gets a skeleton flash on every visit; and it is a second
round-trip after the page has already rendered. `page.tsx` is a server component that
already awaits `getProjectOr404`, so `fetchProjectArticles` can run in the same
`Promise.all` and pass down as a prop. `serverFetch` sends no token, so it returns published
articles only — which is precisely the filter `ArticlesList` applies client-side anyway.

Either wire the server fetcher up or delete it. Leaving both is the worst of the three.

### 5. The article's OG/meta description is raw markdown

`src/web-ui/src/app/projects/[slug]/articles/[articleSlug]/page.tsx:22,26`

```ts
description: article.body.slice(0, 160).trim(),
```

`article.body` is markdown. `## A heading` and `**bold**` and `[text](url)` all go
verbatim into `<meta name="description">` and `og:description`. `ArticleOut` carries both
`summary` (the authored standfirst) and `summary_display` (the server-derived plain-text
excerpt) for exactly this. Commit `808d6846` — "Digest email: strip markdown from the
article excerpt" — shows the team already treats this as a defect elsewhere in the same
branch.

Use `article.summary || article.summary_display`.

### 6. Wheel-zoom in the cropper scrolls the page at the same time

`src/web-ui/src/components/ImageCropper.tsx:122-124`

```tsx
onWheel={(event: ReactWheelEvent) =>
  setZoom((1 / crop.w) * (event.deltaY > 0 ? 0.94 : 1.06))
}
```

Nothing prevents the default, and React attaches `wheel` at the root as a *passive*
listener, so calling `preventDefault()` here wouldn't work either. Scrolling over the stage
zooms the crop **and** scrolls whatever is underneath — inside the listing wizard that's the
dialog's own `overflow-y-auto` container (`ListingImageDialog.tsx:106`), so the stage
slides out from under the pointer mid-adjustment.

`touchAction: "none"` at line 125 already handles the touch equivalent; the wheel case needs
the same treatment via a manually registered non-passive listener on `stageRef`.

### 7. `ArticleRenderContent` bypasses the notifications context

`src/web-ui/src/app/projects/[slug]/articles/[articleSlug]/ArticleRenderContent.tsx:35`

```ts
api.notifications.markArticleThread(article.id).catch(() => {});
```

The context exposes `markArticleRead` (`contexts/notifications.tsx:144-154`) which wraps the
same call in a `finally { await refreshSummary() }`. Every other call site added in this
branch uses it — `NotificationsBell.tsx:107`, `NotificationToaster.tsx:34`,
`NotificationsFeed.tsx:118`. This one doesn't, so opening an article directly leaves the
bell's unread count stale until the 30s poll catches up.

Swap to `useNotifications().markArticleRead`.

### 8. `toListItem` casts past the generated type

`src/web-ui/src/app/projects/[slug]/articles/ArticleCardPreview.tsx:47`

```ts
  } as ArticleListItem;
```

`ArticleListItem` is generated from `backend-openapi.json`, and the whole point of the
generated types is that the compiler notices when the API shape moves. The `as` switches
that off for the one component whose job is to show the author what the real card will look
like — add a field to `ArticleListItem` and this preview silently drifts from the card it is
previewing, with no error.

Right now the object supplies all ten required fields, so the cast looks removable; if
something (probably the local vs. generated `CropRect`) still forces it, narrow the cast to
that one field rather than the whole object.

---

## Minor

### 9. `PublishDialog` rolls its own modal

`src/web-ui/src/app/projects/[slug]/articles/PublishDialog.tsx:13-22` is a `fixed inset-0`
div with a click-outside handler. Every other dialog in this feature —
`ImageAltDialog`, `ListingImageDialog` — uses `components/Dialog.tsx`, which gives a native
`<dialog>`, Escape routed through `onClose`, focus trapping and the top layer for free. This
one has none of that and no `aria-labelledby`. It's twenty lines to convert.

### 10. `isUntouched` mixes the saved title with the live body

`src/web-ui/src/app/projects/[slug]/articles/useArticleDraft.ts:37-44`

```ts
return (
  !article.title.trim() &&      // last saved
  !body.trim() &&               // live, from bodyRef
  ...
```

`article.title` is whatever was last persisted; the body is read live. On `/new`, typing only
a headline and leaving deletes the draft and the headline with it. Low blast radius, but a
predicate that reads two different points in time is a bug waiting for its second reader.
Take the title from the form.

### 11. The wizard's "full-screen under sm" can't take effect

`src/web-ui/src/app/projects/[slug]/articles/ListingImageDialog.tsx:95` passes
`max-sm:rounded-none max-sm:max-h-screen max-sm:min-h-screen`, but that class string lands
on `Dialog`'s *inner* div. The `<dialog>` element itself is hard-coded
`w-[calc(100%-2rem)] max-h-[calc(100%-2rem)]` (`components/Dialog.tsx:44`), so on a 375px
screen the wizard still has a 1rem gutter on all sides and is still height-capped — only the
corners change. Either give `Dialog` a `fullScreenOnMobile` prop or drop the classes; as it
stands the comment above them describes something that doesn't happen.

### 12. `useImageUpload` memoisation is defeated by an inline target

Three call sites pass a fresh object literal: `ListingImageDialog.tsx:58`,
`ProjectDetail.tsx:57` and `:69`. `uploadFile` lists `target` in its `useCallback` deps
(`hooks/useImageUpload.ts:100`), so it gets a new identity on every render and the
`useCallback` buys nothing. Wrap the target in `useMemo` at the call sites, or destructure
it into primitive deps inside the hook.

### 13. No unsaved-changes guard

The body lives only in `bodyRef` until a save. The breadcrumb `Link` at
`ArticleAuthoringPage.tsx:122`, browser Back, and any in-app navigation all discard it
silently. For a page that is entirely a text editor, a `beforeunload` handler plus a
confirm on the breadcrumb is the minimum.

### 14. The card preview links to a dead URL for drafts

`ArticleCardPreview.tsx:56`: `` `/projects/${projectRef}/articles/${article.slug ?? ""}` ``.
`ArticleOut.slug` is nullable and drafts have no slug, so the preview card in the listing tab
is a live link to `/articles/` — which is the state the tab is most used in. Render the
preview as a non-link when there's no slug.

### 15. The author's framing doesn't reach social cards

`[articleSlug]/page.tsx:28` puts `listing_image_url` — the uncropped original — into
`og:image`. Cropping is applied in CSS at render (`CroppedImage.tsx:87-95`), so nothing an
author does in the wizard affects what Facebook or Slack shows. That is inherent to the
CSS-crop decision and probably the right trade, but it deserves a line in the code or the
design doc so the next person doesn't file it as a bug.

### 16. Wizard orphan on a change of mind

`ListingImageDialog.tsx:76-82` discards `pendingUpload` on Cancel and on Remove, but not
when the author uploads, presses Back, then selects a *different* existing image and
confirms. The upload survives unreferenced. The comment already frames this as best-effort
and article images stay out of the project gallery, so the orphan is invisible — noting it
so the omission is deliberate rather than forgotten.

---

## Not raised

Checked and found fine: `backend-openapi.json` is regenerated and current; `api-types.ts`
correctly absent (gitignored); the sanitize pipeline order is right (`rehypeRaw` →
`rehypePrismPlus` → `rehypeSanitize` last) and `markdown-parity.test.tsx` covers `<script>`,
`javascript:` URLs, `on*` handlers and the `style` attribute; `readImageDimensions` avoids
blob URLs for the documented CSP reason and degrades to `null` rather than throwing;
`article-markdown.css` is route-scoped rather than dumped into `globals.css`; the test
harness matches the repo's existing raw-`createRoot` convention; the `follows` API rename
from per-channel preferences to follow/unfollow is applied consistently across
`FollowPopover`, the Following page and the client.

## Verdict

Address blockers 1 and 2 before merge — both are visible to an author on the first run
through the feature, and 2 points at an unused export that shouldn't have survived. 3–8 are
worth doing in the same pass; the rest can be follow-ups. The underlying component
architecture is sound and I'd merge on top of it once the two blockers are closed.
