# Frontend review — `d2463b33...7a20fb38`, `src/web-ui/**`

Scope: the new `app/projects/[slug]/articles/**` cluster, the shared crop/upload/card
components it introduced, and the follow/notification changes that came with it.

## Architecture & maintainability

### 1. The article reader ships the whole markdown toolchain to the browser

`src/web-ui/src/app/projects/[slug]/articles/[articleSlug]/ArticleRenderContent.tsx:1`
is `"use client"` and imports `react-markdown`, `rehype-raw`, `rehype-prism-plus` and
`rehype-sanitize` at module scope (lines 6–11). The default export of
`rehype-prism-plus` is built on `refractor/all` (verified in
`node_modules/rehype-prism-plus/dist/index.es.js`: `import{refractor as o}from"refractor/all"`),
i.e. all ~297 Prism grammars, 2.7 MB of source in `node_modules/refractor/lang`.
`rehype-raw` drags in `parse5`. All of it lands in the route chunk for a page whose
only genuinely client-side needs are `useAuth` and the mark-read effect at lines 37–42.

This also breaks with the rest of the app: `app/about/why/page.tsx`,
`app/about/prizes/page.tsx` and `app/privacy/page.tsx` all render `ReactMarkdown`
inside server components.

Direction: render the body in the server component (`[articleSlug]/page.tsx`) and
reduce the client surface to a small `<ArticleReadMarker articleId>`. If the render
must stay on the client, at minimum import `rehype-prism-plus/common` — the editor
only offers 12 languages (`ArticleEditor.tsx:80–93`), so `all` is paying for 285
grammars nobody can produce.

### 2. `useArticleDraft` owns five unrelated concerns

`src/web-ui/src/app/projects/[slug]/articles/useArticleDraft.ts` is 386 lines and
returns a 21-member object. It owns: form state; the eager draft creation on `/new`
plus the `router.replace` that follows it (lines 104–124); the untouched-draft sweep
on unmount (lines 162–170); the `beforeunload` guard (lines 208–215); and
save/publish/delete including two more `router.push` calls (lines 322, 345).

Routing decisions inside a state hook are what forced the `latestRef.current.leaving`
flag (lines 83–91) — a mutable "am I about to be unmounted" bit that three separate
call sites must remember to set, and that is read from a cleanup function which by
construction sees a stale snapshot. Findings B1 and B2 below both come out of this
design.

Direction: split persistence (`save`/`publish`/`delete`, pure, returns results) from
lifecycle (create-on-mount, sweep), and move all `router.*` calls up into
`ArticleAuthoringPage`, which is the component that actually knows what navigation
means. Better still, drop the eager-create/sweep pair: have the backend reap
provisional drafts, or create the draft on the first upload rather than on mount.

### 3. `ArticleFormState.body` is a field that is always wrong

`useArticleDraft.ts:16–28` declares `body` on the form, but the live body lives in
`bodyRef` (line 78) and only reaches the form when `snapshotForm()` is called
(lines 182–187). Between calls, `form.body` holds whatever the last save wrote.
Three code paths currently remember to snapshot first; a fourth that forgets will
silently persist a stale body, and nothing in the type system says so. The safety
comment at lines 180–181 is doing work that a type should be doing.

Direction: remove `body` from `ArticleFormState` and have the snapshot function
return a distinct `ArticleSavePayload = ArticleFormState & { body: string }`. Then
"persist without snapshotting" stops compiling. `ArticleAuthoringPage.tsx:264` wants
`form.body` only as `initialMarkdown`, which can come off `article.body` instead.

### 4. Three layers of upload code with two different status models

- `src/web-ui/src/lib/uploadImage.ts` — the actual 3-step upload, callback-based.
- `src/web-ui/src/hooks/useImageUpload.ts` — wraps it in a `UploadProgress[]` list.
- `src/web-ui/src/app/projects/[slug]/articles/useImageUploadStatus.ts` — wraps it
  again in an `ImageUploadStatus` union.

`ListingImageDialog.tsx:82` takes the middle one and then uses only `isUploading`,
discarding the `uploads` array entirely; its errors go through `onError` into local
state (line 90). So the dialog reimplements what `useImageUploadStatus` already is.
Two hooks, two error vocabularies, one shared core.

Direction: one hook over `lib/uploadImage.ts` with an optional progress list; delete
whichever of the two wrappers loses.

### 5. 16:9 is defined twice, under two names, in two files

`components/CroppedImage.tsx:24` exports `DEFAULT_RATIO = 16 / 9`;
`ListingImageDialog.tsx:15` declares a private `CARD_RATIO = 16 / 9` whose comment
says it mirrors `services/articles/crop.py`. Four more `aspect-[16/9]` literals sit
in `ListingImageDialog.tsx:275,293`, `ListingSettingsPanel.tsx:84` and
`ArticlesList.tsx:66–69`. Three definitions of the same contract in one feature.
Export one constant from `CroppedImage.tsx` and have the Tailwind classes derive from
it or be replaced by `<CroppedImage crop={null}>`.

### 6. Smaller

- `ArticleAuthoringPage.tsx:45` computes `projectRef`, then line 84 writes
  `project.slug ?? project.id` out again 39 lines later.
- `ImageCropper.tsx:77` — `const crop = value ?? defaultCrop(source)` allocates a new
  object every render when `value` is null, so `setZoom` (line 93) changes identity
  every render and the non-passive wheel listener (lines 114–123) is torn down and
  re-attached on every render, including during a drag. Wrap in `useMemo`.
- `sanitize-schema.ts:32–37` — the `align` on `div` and `width`/`height` on `img`
  additions are no-ops: `defaultSchema.attributes['*']` already contains all three
  (`node_modules/hast-util-sanitize/lib/schema.js:76,105,136`). The comments claim
  they are load-bearing, so the next person will keep them forever.

## Latent bugs

### Blocker

**B1. Leaving the editor while an inline image is uploading deletes the whole draft.**

`useArticleDraft.ts:162–170` deletes the article on unmount when
`isUntouched(article, form, bodyRef.current)` (lines 43–54) holds. That predicate
reads `article.images.length === 0`, and nothing updates `article.images` for inline
uploads: `useImageUploadStatus.ts:25–41` uploads through `sendUpload` and returns a
URL to MDXEditor; it never touches draft state. Only `chooseListingImage`
(`useArticleDraft.ts:227–231`) ever adds to `article.images`.

MDXEditor's `insertImage$` awaits the upload handler before inserting the node, so
during the upload the body is still empty.

Failure: author opens `/projects/x/articles/new`, is redirected to `/edit/<id>`,
clicks the toolbar image button and picks a 8 MB photo. While the S3 PUT is in flight
they click the project breadcrumb. `isDirty()` (lines 192–203) is false — empty title,
empty `bodyRef`, form equals article — so the confirm at `ArticleAuthoringPage.tsx:154`
does not fire. The hook unmounts, `isUntouched` is true, and
`api.articles.delete(projectRef, current.id)` runs. The draft is gone, the upload
completes against a deleted article (the `complete` call 404s), and the author is told
nothing. Same result if they hit Back or click any in-app link during the upload.

Fix: track in-flight uploads in the hook (the editor already funnels all three insert
routes through one handler) and refuse the sweep while any are pending — or stop
sweeping and reap provisional drafts server-side.

### Important

**B2. Text typed in the seconds after `/new` opens is silently discarded.**

`useArticleDraft.ts:113–137`: on the `/new` route the hook creates the draft, issues
`router.replace('/projects/…/articles/edit/<id>')`, and then — without waiting for
that navigation — sets `article`, `form` and `isLoading = false`. The page therefore
renders a fully interactive editor (title input at `ArticleAuthoringPage.tsx:221`,
channel dropdown, body editor) while the App Router is still fetching the RSC payload
for the `edit/[articleId]` route, which includes a server-side `getProjectOr404` call
(`edit/[articleId]/page.tsx:10`).

`/new/page.tsx` and `/edit/[articleId]/page.tsx` are distinct pages, so when the
navigation lands `ArticleAuthoringPage` remounts and `useArticleDraft` refetches the
article from the server — which still has `title: ""`, `body: ""`.

Failure: on a slow connection or a cold backend, the author types a headline in the
~0.5–3 s window and watches it disappear when the URL changes. No prompt, no error.

Fix: swap the URL with `window.history.replaceState` rather than a route change, or
keep `isLoading` true on the create path until the navigation has committed.

**B3. Clicking the "Listing settings" tab pushes unsaved edits live on a published
article.**

`ArticleAuthoringPage.tsx:131–141` calls `await draft.save()` before opening the
listing tab. `save()` → `persistDraft` → `api.articles.update(...)` with the full body
(`useArticleDraft.ts:263–271`), and the endpoint is the same one whether the article is
a draft or published — `draft.isPublished` only changes the button label
(`ArticleAuthoringPage.tsx:183–186`).

Failure: an author opens a published article to check how the card looks, makes a
half-finished edit or an accidental keystroke in the body, clicks "Listing settings",
and that text is now live on `/projects/x/articles/<slug>`. The tab is not labelled as
a save and there is no confirmation.

Fix: for a published article, either confirm before the implicit save or render the
preview from the last-saved article and drop the save entirely.

**B4. A slow save can revert a listing image the author picked while it was in flight.**

`useArticleDraft.ts:275–284`: after `api.articles.update` returns, `persistDraft`
overwrites `form.listing_image_id`, `listing_crop` and `listing_image_mode` with the
server's values, using a functional update that ignores whatever the author did in the
meantime. Nothing blocks the wizard during a save — `ListingSettingsPanel.tsx:92`
("Change…") has no `disabled`, and neither does "Use it" in
`ListingImageDialog.tsx:206`.

Failure: on the listing tab the author clicks Save; the request stalls (slow upload of
a long body, backend under load). They open the wizard, pick a different image, frame
it and confirm. The stalled save then returns and `setForm` puts the old
`listing_image_id`/`crop` back. The panel and the card preview snap back to the
previous image, and the author's choice is lost unless they notice and redo it.

Fix: guard the response merge with a request generation counter, or disable the image
controls while `isSaving`.

### Minor

**B5. API-layer error strings are shown verbatim to authors.**
`useArticleDraft.ts:141`, `:287`, `:347` all do
`err instanceof Error ? err.message : "…"`. `APIClient.request` throws bare
`new Error("Token refresh failed")` on the transient path and `new Error("Unauthorized")`
on the invalid path (`lib/api/base.ts:137,143,151`). During a backend blip the author
sees "Token refresh failed" in red next to the Save button and cannot tell whether the
article was saved or whether they have been logged out. (They have not — the tokens are
correctly kept.) Narrow on `ApiRequestError` for the messages worth showing and use a
fixed Icelandic-neutral sentence for the rest; `publish()` at lines 324–329 already
does this properly and is the pattern to copy.

**B6. `void markArticleRead(...)` produces an unhandled rejection on any failure.**
`contexts/notifications.tsx:144–152` has `try { … } finally { await refreshSummary() }`
with no `catch`, so the promise rejects on a network blip. Three call sites discard it
with `void`: `NotificationsBell.tsx:105`, `NotificationToaster.tsx:35`,
`NotificationsFeed.tsx:132`. `ArticleRenderContent.tsx:39` gets this right with
`.catch(() => {})`. Clicking a notification while offline throws into the console (and
the Next dev overlay).

**B7. The sanitiser allows arbitrary class names on `span` and `pre`.**
`sanitize-schema.ts:38–40` adds a bare `"className"` for `pre`/`code`/`span`, which in
`hast-util-sanitize` means "any value" (`lib/index.js:614–650`: an allow-list only
applies when the definition array has more than one entry). Articles are authored by
any `full_edit` contributor and `rehypeRaw` runs first, so an author can write
`<span class="fixed inset-0 z-50 bg-white">` in the body; those utilities exist in the
compiled Tailwind CSS, so the span covers the viewport of their own article page. Not
script execution — everything else in the schema holds — but it is more than syntax
highlighting needs. Restrict to a regex: Prism only emits `token`, its token-type
names, `code-highlight`, `code-line`, `line-number`, `highlight-line` and
`language-*`.

**B8. The listing wizard leaks the first upload when a second replaces it.**
`ListingImageDialog.tsx:84–90` sets `pendingUpload` to each completed upload without
discarding the previous one; only `discardPendingUpload` (line 108) deletes, and it
only ever sees the latest. Upload A, click "Back", upload B, confirm B: A stays linked
to the article. Because the picker lists `article.images` — the image-article link, not
the body (`useArticleDraft.ts:356–359`) — A is offered again the next time the wizard
opens, as an image the author believes they discarded.

**B9. `uploadImage` cannot fail before the presign, contrary to its comment.**
`lib/uploadImage.ts:50–52` says dimensions are read first "so a decode failure fails the
upload early rather than leaving a completed row with no dimensions", but
`readImageDimensions` (line 121) returns `null` on every failure path and never throws.
The row is completed without dimensions and the image is then rejected by
`isCroppable` (`ListingImageDialog.tsx:27`) with "We couldn't read that image's
dimensions". The behaviour may be the one you want; the comment is not describing it.

**B10. An article notification with no slug deep-links to the discussion tab.**
`lib/notifications.ts:5–7` only takes the article branch when `group.article_slug` is
set, but `groupKey` (line 33) keys an article group off `article_id` alone. A group
that reaches the UI without a slug renders a row whose href is
`/projects/<slug>?comment=undefined#discussions`.

## Test coverage gaps

- **The unmount sweep is tested only against synchronous state.**
  `use-article-draft.test.tsx:270–309` covers title/body/existing-content, but not an
  in-flight inline upload (B1) — the case that actually loses data. Needs a test that
  starts an upload, unmounts, and asserts `articles.delete` was not called.
- **`publish()` and `remove()` are untested.** No `describe` block in
  `use-article-draft.test.tsx` touches either: the 422 `detail` extraction
  (`useArticleDraft.ts:324–329`), the `leaving` flag on publish/delete, or the fact that
  publish saves first.
- **The tab-switch save (B3) is untested.** `ArticleAuthoringPage.handleTabClick` has no
  unit or e2e coverage at all.
- **`hooks/useImageUpload.ts` has no tests** despite being rewritten onto the new
  `UploadTarget` API. Untested: `uploadFiles` running several `uploadFile` calls
  concurrently, and the failure path before `onImageId` fires, where the catch tries to
  mark a row by filename that was never added (`useImageUpload.ts:91–97`).
- **`readImageDimensions` is untested** (`lib/uploadImage.ts:121–152`). It is the sole
  input to the croppable/uncroppable branch that `listing-image-dialog.test.tsx` spends
  three tests on, but the `createImageBitmap`-throws → data-URL fallback → `null` chain
  is never exercised.
- **`publishedNewestFirst` and `sortDraftsFirst` are untested** (`ArticlesList.tsx:20`,
  `MyProjectArticles.tsx:23`) — including the `state === "published" && slug` filter
  that stops an author's own drafts leaking into the public tab.
- **Sanitiser tests stop short of two cases.** `markdown-parity.test.tsx:95–149` covers
  `<script>`, `style`, `on*` and `javascript:` in `img src`, but not `javascript:` in
  `<a href>` and not arbitrary `class` on `span`/`pre` (B7).
- **No Playwright coverage of the `/new` → `/edit` URL swap** (B2); both new e2e specs
  start from an already-created article.

## Checked and clean

- **Auth resilience.** `lib/api/base.ts` is not in the diff — the
  `"refreshed" | "invalid" | "transient"` split is untouched, transient failures still
  keep the tokens (lines 140–143), and nothing new calls `clearTokens`.
- **No error-as-empty-data caching.** `ArticlesList.tsx:33–54`, `MyProjectArticles.tsx:38–53`,
  `profile/following/page.tsx:22–38` and `FollowPopover.tsx:26–41` all keep `null` plus an
  error string rather than falling back to `[]`. `projects/[slug]/page.tsx:70` passes
  `null` (not `[]`) when the server-side article fetch fails, so the client refetches
  instead of caching an empty listing — and `initialArticles === []` is still truthy, so
  a genuinely empty project renders "No articles yet" rather than re-fetching.
- **Markdown sanitisation.** `articleSanitizeSchema` extends `hast-util-sanitize`'s
  GitHub schema: allow-list tag names (no `iframe`/`object`/`form`), `script` in `strip`,
  `protocols` limited to http/https/mailto/irc/xmpp, no `style`, no `on*` route (only
  named attributes survive), `clobberPrefix` intact. `rehypeSanitize` is last in the
  plugin array (`ArticleRenderContent.tsx:113–117`), after `rehypeRaw` and
  `rehypePrismPlus`, which is the correct order.
- **Image dimensions.** `readImageDimensions` deliberately avoids `blob:` URLs (the CSP
  in `next.config.ts` allows `data:` but not `blob:` under `img-src`), uses
  `createImageBitmap` with a data-URL fallback, and returns `null` rather than `0×0`.
  `isCroppable` (`ListingImageDialog.tsx:27`) narrows on `width && height` before
  anything reaches `defaultCrop`/`layoutFor`, so no divide-by-zero or `NaN` gets into
  the crop maths. `layoutFor` also guards `crop.w` (line 303) and `pan` bails on a zero
  layout (line 100).
- **Crop maths agreement.** `ImageCropper`'s preview and `CroppedImage` share
  `CROP_BACKGROUND` and the same rect, and the cropper clamps zoom to
  `[MIN_ZOOM, zoomCeiling]` so `crop.w` cannot reach 0. An out-of-range `x`/`y` is
  intentional and handled by `insetStyle`.
- **Generated types.** `lib/api/articles.ts` and `lib/api/channels.ts` alias
  `components["schemas"][...]` throughout; no hand-rolled request/response interfaces.
  The one deliberate duplicate, `CropRect` in `CroppedImage.tsx:9`, is checked at the
  boundary anyway — it flows into `api.articles.update`'s `ArticleUpdate` argument, so a
  backend rename would fail to compile. `toListItem` (`ArticleCardPreview.tsx:26`) builds
  a generated `ArticleListItem`, so a new required field is a compile error, not a
  silent gap.
- **Client/server boundary.** All three new `page.tsx` files are server components
  importing only `@/lib/api/server` (which is `import "server-only"`); every new
  component that uses hooks or browser APIs carries `"use client"`; the
  `dynamic(..., { ssr: false })` at `ArticleAuthoringPage.tsx:16` sits inside a client
  component, which is where Next 16 requires it.
- **`useChannelToggle`** uses functional updates throughout, so concurrent toggles do
  not clobber each other and a failure rolls back only its own channel —
  `use-channel-toggle.test.tsx:164,190` covers both.
- **Icelandic strings.** Nothing to flag: the app is English apart from the brand name
  (`components/Navigation.tsx:58`), and there is no localisation infrastructure to break
  with. The new strings are consistent with the rest of the UI.
