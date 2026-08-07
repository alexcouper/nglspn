# 04. Leaving the editor mid-upload deletes the draft

**Finding:** I4 — the unmount sweep deletes an article that looks empty, and an in-flight inline upload leaves it looking empty.
**Alex:** "I don't really follow what the problem case is here. Is this only when first starting a draft, if you navigate away whilst starting you don't get it? or is this navigating away mid upload of an image on the draft results in the whole draft being deleted regardless of the state?"
**Type:** answer (with a fix proposal at the end)
**Effort:** S for the guard itself (~40 lines across three files, one new prop chain), M if the server-side reaper follow-up is taken.

## What is actually happening

### The mechanism, in order

1. `useArticleDraft.ts:162–170` registers a cleanup that runs on unmount of
   `ArticleAuthoringPage`. It deletes the article when
   `isUntouched(article, form, bodyRef.current)` holds and `state.leaving` is false.
2. `isUntouched` (`useArticleDraft.ts:43–54`) is four conjuncts:

   ```ts
   !(form?.title ?? article.title).trim() &&
   !body.trim() &&
   !(form?.listing_image_id ?? article.listing_image_id) &&
   article.images.length === 0
   ```

   The first three read live client state. The fourth reads `article.images`, which
   is only ever written by a server response (`api.articles.get` / `create` /
   `update`) or by `chooseListingImage` (`:227–231`).
3. An inline upload does not touch any of the four. `useImageUploadStatus.ts:25–41`
   calls `sendUpload(...)`, gets back a full `ProjectImage`, throws away everything
   but `image.url`, and returns that URL to MDXEditor. It never calls `setArticle`.
4. MDXEditor inserts the node only after the handler resolves. Verified in
   `node_modules/@mdxeditor/editor/dist/plugins/image/index.js:30–43`:

   ```js
   imageUploadHandler(values.file).then(handler)   // handler → internalInsertImage$
   ```

   The drop path (`:259–283`) is the same shape (`Promise.all(...).then(...)`), and
   the paste path (`:137–138`) too. So for the entire duration of the presign →
   S3 PUT → complete round trip, the body markdown is unchanged and `bodyRef.current`
   is whatever it was before.

So during an upload, all four conjuncts can hold simultaneously — and nothing about
the upload is visible to the sweep.

### Answering the two questions directly

**Q1: "is this only when first starting a draft?"**

The *deletion* is never performed by the `/new` mount. `useArticleDraft.ts:122` sets
`latestRef.current.leaving = true` before the `router.replace`, precisely so the
`/new` unmount does not eat the draft it is navigating to. The sweep that fires is
always the one registered by the `/edit/<id>` mount.

But the *article being deleted* is not restricted to a just-created draft.
`isUntouched` does not look at `article.state`, `created_at`, or whether the article
arrived from the server with content. It asks only "does this look empty right now".
An article that the author has just blanked is indistinguishable from one that was
always empty. See S9 and S10 below.

**Q2: "does navigating away mid-upload delete the draft regardless of the state?"**

**No.** A draft with real typed content is not at risk. If the title field has
anything in it, or the editor body has anything in it, or a listing image is
selected, or the loaded article already had images, the sweep does not run.

The upload case only bites when the author's *first* action in an otherwise-empty
draft is inserting an image, and they leave before the upload finishes.

### The scenarios

`form.title` and `body` are the live values at the moment of unmount; `images` is
`article.images` as the client last saw it.

| # | What the author did | `form.title` | `bodyRef.current` | `article.images` | `listing_image_id` | Confirm fires? | Draft deleted? |
|---|---|---|---|---|---|---|---|
| S1 | Opened `/new`, left immediately | `""` | `""` | `[]` | `null` | no (not dirty) | **yes** — intended |
| S2 | Typed a headline, left | `"Foo"` | `""` | `[]` | `null` | yes | no |
| S3 | Typed body text, left | `""` | `"prose"` | `[]` | `null` | yes | no |
| S4 | Empty draft, inserted an image, left **during** the upload | `""` | `""` | `[]` | `null` | **no** | **yes — the bug** |
| S5 | Same, but the upload finished and the node was inserted | `""` | `"![](url)"` | `[]` | `null` | yes | no |
| S6 | Upload finished, author deleted the image markdown from the body, left | `""` | `""` | `[]` (stale — server has 1) | `null` | no | **yes** |
| S7 | Typed a headline, then started an upload, left mid-upload | `"Foo"` | `""` | `[]` | `null` | yes | no |
| S8 | Opened an existing draft with saved title+body, left | `"Foo"` | `"prose"` | `[]` | `null` | no (clean) | no |
| S9 | Opened an existing draft, cleared the title and select-all-deleted the body, left | `""` | `""` | `[]` | `null` | yes on the breadcrumb only | **yes — whole article** |
| S10 | Same as S9 on a **published** article | `""` | `""` | `[]` | `null` | yes on the breadcrumb only | **yes — published article gone** |
| S11 | Any article whose server copy has images | — | — | `[img]` | — | — | no |
| S12 | Listing image chosen in the wizard | — | — | adopted at `:227` | set | — | no |

Two notes on the table:

- S6 is the "upload succeeded, then removed" variant. `article.images` is still the
  stale `[]` the client loaded, because nothing refreshes it after an inline upload.
  The draft is genuinely empty of prose, so deleting it is arguably the intent — but
  the `ProjectImage` row cascades with it (`apps/projects/models.py:238`) and the S3
  object is orphaned unrecoverably (that is finding I2). The author may also have
  been keeping that upload to use as a listing image; it is offered by the wizard
  from `article.images`, not from the body.
- S9/S10: the confirm at `ArticleAuthoringPage.tsx:154` is on the breadcrumb link
  only. The global nav links (`components/Navigation.tsx`) have no such handler, so
  leaving by the top nav is silent. And the prompt, if it does fire, says "Leave
  without saving?" — nothing about deletion. `beforeunload` (`:208–215`) covers the
  reload/close case, and it too says nothing about deletion.

### How wide is the window, honestly

For S4: **narrow precondition, wide window.** The precondition is "the first thing
the author does in an empty draft is insert an image, before typing anything". That
is not the common flow — most people type a headline first, and a headline is enough
to protect them (S7). The window itself, once entered, is the full upload: presign
round trip + S3 PUT + completion call. For a 8 MB photo on a domestic uplink that is
tens of seconds, not milliseconds.

For S9/S10: **no timing window at all.** It is deterministic. Clear a short article's
title and body, leave, and the article is deleted from the server — including a
published one, which is then gone from the public listing.

### Re-grading

The review filed I4 as a **blocker** on the strength of the upload race. On the
honest reading:

- The upload race (S4/S6) is **Important**, not a blocker. Real data loss, silent,
  but it needs an unusual authoring order.
- The predicate's *other* failure (S9/S10) is the blocker. The review missed it. It
  is the same line of code — `isUntouched` has drifted from "the empty draft `/new`
  just created", which its own comment at `:37–42` claims it means, to "any article
  that currently looks empty".

Both fall out of one fix, below.

## Proposed change

Three parts. All in the frontend; no backend change required for the fix itself.

### Part 1 — the sweep must know about uploads

`useArticleDraft` gains an upload registry. Two refs, because the sweep cleanup reads
them synchronously and cannot see state that has not committed yet:

```ts
// useArticleDraft.ts, next to bodyRef (line 78)

// Inline uploads are invisible to `article.images` until a save, and MDXEditor
// does not insert the image node until the upload resolves — so between the file
// picker and the insert, a draft with an upload in flight looks untouched.
const pendingUploadsRef = useRef(0);
const uploadedImageIdsRef = useRef<string[]>([]);
```

```ts
// new callbacks, next to chooseListingImage (line 220)

const beginImageUpload = useCallback(() => {
  pendingUploadsRef.current += 1;
}, []);

const finishImageUpload = useCallback((image: ProjectImage | null) => {
  pendingUploadsRef.current = Math.max(0, pendingUploadsRef.current - 1);
  if (!image) return;
  uploadedImageIdsRef.current = [...uploadedImageIdsRef.current, image.id];
  // Same adoption chooseListingImage does at :227 — so the listing wizard offers
  // an inline upload without waiting for a save.
  setArticle((prev) =>
    prev && !prev.images.some((existing) => existing.id === image.id)
      ? { ...prev, images: [...prev.images, image] }
      : prev,
  );
}, []);
```

The refs, not the state, are what the sweep consults. `finishImageUpload` runs the
ref update synchronously and queues the `setArticle`; if the unmount lands between
those two, the state copy is lost but the ref is already correct.

Extract the three lines shared with `chooseListingImage` into a local
`adoptImage(image)` while you are in there.

### Part 2 — tighten the predicate to what its comment claims

Replace `isUntouched` (`:43–54`) with a predicate that only ever discards a draft
that *arrived* empty and is still empty:

```ts
interface LeaveState {
  article: Article;
  form: ArticleFormState | null;
  body: string;
  // True when the article was already blank when this page loaded it. A saved
  // article the author has just blanked is not an untouched draft, and deleting
  // it is not a sweep — it is data loss the author did not ask for.
  arrivedEmpty: boolean;
  pendingUploads: number;
  uploadedImageIds: readonly string[];
}

function shouldDiscardDraft(state: LeaveState): boolean {
  if (state.article.state !== "draft") return false;
  if (!state.arrivedEmpty) return false;
  if (state.pendingUploads > 0) return false;
  if (state.uploadedImageIds.length > 0) return false;
  return (
    !(state.form?.title ?? state.article.title).trim() &&
    !state.body.trim() &&
    !(state.form?.listing_image_id ?? state.article.listing_image_id) &&
    state.article.images.length === 0
  );
}
```

`arrivedEmpty` is recorded once, in the load effect, right where `setArticle(loaded)`
happens (`:127`):

```ts
arrivedEmptyRef.current =
  !loaded.title.trim() &&
  !loaded.body.trim() &&
  !loaded.listing_image_id &&
  loaded.images.length === 0;
```

The sweep becomes:

```ts
useEffect(() => {
  const state = latestRef.current;
  return () => {
    const current = state.article;
    if (state.leaving || !current) return;
    if (
      !shouldDiscardDraft({
        article: current,
        form: state.form,
        body: bodyRef.current,
        arrivedEmpty: arrivedEmptyRef.current,
        pendingUploads: pendingUploadsRef.current,
        uploadedImageIds: uploadedImageIdsRef.current,
      })
    )
      return;
    api.articles.delete(projectRef, current.id).catch(() => {});
  };
}, [projectRef]);
```

Each guard maps to a row: `state !== "draft"` → S10, `arrivedEmpty` → S9,
`pendingUploads` → S4, `uploadedImageIds` → S6.

### Part 3 — wire the callbacks through

`ArticleAuthoringPage.tsx:261–266`:

```tsx
<ArticleEditor
  projectRef={projectRef}
  articleId={article.id}
  initialMarkdown={form.body}
  onChange={draft.handleBodyChange}
  onUploadStart={draft.beginImageUpload}
  onUploadSettled={draft.finishImageUpload}
/>
```

`ArticleEditor.tsx:37–56` — two new props, passed straight down:

```ts
const { status, uploadImage, dismissError } = useImageUploadStatus(
  projectRef,
  articleId,
  onUploadStart,
  onUploadSettled,
);
```

`useImageUploadStatus.ts:22–41`:

```ts
export function useImageUploadStatus(
  projectRef: string,
  articleId: string,
  // Positional and individually stable rather than an options object: they land
  // in the deps of `uploadImage`, which is the imagePlugin's upload handler, and
  // a fresh object per render would churn the plugin's params every keystroke.
  onStart?: () => void,
  onSettled?: (image: ProjectImage | null) => void,
) {
  const [status, setStatus] = useState<ImageUploadStatus>({ kind: "idle" });

  const uploadImage = useCallback(
    async (file: File) => {
      setStatus({ kind: "uploading" });
      onStart?.();
      try {
        const image = await sendUpload(
          { kind: "article", projectRef, articleId },
          file,
        );
        setStatus({ kind: "idle" });
        onSettled?.(image);
        return image.url;
      } catch (err) {
        setStatus({ kind: "error", message: messageFor(err) });
        onSettled?.(null);
        throw err;
      }
    },
    [projectRef, articleId, onStart, onSettled],
  );
```

`beginImageUpload`/`finishImageUpload` are `useCallback(..., [])`, so the deps are
stable and nothing changes for MDXEditor.

### Options considered and rejected

1. **Client-side guard (above).** Recommended. Small, testable, fixes all four rows.
2. **Stop sweeping on the client; reap provisional drafts server-side.** A management
   command deleting `state="draft"` articles with empty title/body/images older than
   an hour. This is the only approach that survives a killed browser or a crashed
   tab, which the client sweep has never handled. It loses on its own because the
   empty draft sits in the author's list in the meantime and the code that creates it
   is the code that should know it is disposable. Worth doing **in addition**, as a
   follow-up — it is the backstop for every case the client cannot reach.
3. **Don't create the draft eagerly at all.** Removes the whole class: no empty draft
   exists, so nothing needs sweeping. This is the right end state and is written up
   as option (b) in `05-new-route-typing-lost.md` and as Follow-up D in
   `10-use-article-draft-refactor.md`. It is too large for this branch.

Take 1 now, schedule 2, aim for 3.

## Tests

Vitest, `use-article-draft.test.tsx`, in the `"the untouched-draft sweep"` block
(`:270–309`). The existing four tests keep passing unchanged.

- `keeps a draft while an inline upload is in flight` — mount with `articleId`, call
  `draft.beginImageUpload()`, unmount, assert `articles.delete` was not called. This
  is the test the frontend review's coverage-gap list asks for.
- `keeps a draft whose only content is an image the author removed from the body` —
  `beginImageUpload()`, `finishImageUpload(image())`, `handleBodyChange("")`,
  unmount, assert no delete.
- `sweeps once a failed upload has settled` — `beginImageUpload()`,
  `finishImageUpload(null)`, unmount, assert delete *was* called. Guards the counter
  against leaking.
- `keeps a published article the author blanked` —
  `articles.get.mockResolvedValue(article({ state: "published", title: "Live" }))`,
  `updateForm({ title: "" })`, `handleBodyChange("")`, unmount, assert no delete.
- `keeps an article that had content when it loaded` — same but `state: "draft"`;
  covers `arrivedEmpty`.

If `shouldDiscardDraft` is extracted as a pure function (recommended in
`10-use-article-draft-refactor.md`), the last three belong in a plain
`article-draft-state.test.ts` with no mounting at all, and only the in-flight one
needs the React harness.

Playwright, `e2e/article-images.spec.ts`: route-intercept the presigned PUT with a
delay, click Insert image, pick a fixture file, click the breadcrumb while the
status bar still says uploading, and assert the article is still listed under
`/my-projects/<id>#articles`. Note the PUT goes to the S3 host, not the app origin,
so the `page.route` pattern has to be a glob over the bucket URL.

## Risks and what this does not cover

- **A killed tab is still unprotected.** `beforeunload` cannot cancel or await an
  in-flight upload, and the sweep never runs. The draft survives as an empty row in
  the author's list — a leak, not a loss. Option 2 is the only fix.
- **A failed upload re-arms the sweep immediately.** After `finishImageUpload(null)`
  the counter is zero, so leaving while the red error bar is showing deletes the
  draft. That is correct — nothing was uploaded — but it is a behaviour worth being
  deliberate about rather than discovering.
- **Behaviour change in the listing wizard.** Adopting the uploaded image into
  `article.images` means the wizard now offers inline uploads before a save. Today it
  does not. This is an improvement, but it is a visible change and
  `listing-image-dialog.test.tsx` should be read for assumptions about the list.
- **Does not fix I2.** When the sweep does legitimately delete a draft that has image
  rows, `api.articles.delete` still cascades them and orphans the S3 objects. The
  `uploadedImageIds` guard makes that rarer; it does not make it impossible.
- **Does not fix B8.** The listing wizard still leaks the first upload when a second
  replaces it. Separate path (`ListingImageDialog.tsx:84–90`), separate fix.
- **`arrivedEmpty` is per-mount.** With the current `/new` → `/edit` route change, the
  `/edit` mount computes it from its own GET, which returns the empty draft `/new`
  just created — so the sweep still works as intended. If `05-new-route-typing-lost.md`
  option (c) is taken, there is only one mount and `arrivedEmpty` becomes exactly
  "this session created it", which is stronger. The two fixes compose; neither
  depends on the other.
