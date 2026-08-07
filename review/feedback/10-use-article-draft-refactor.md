# 10. Decomposing `useArticleDraft`

**Finding:** Architecture point 1 — 386 lines, a 21-member return, and it owns routing, eager draft creation, the unmount sweep, `beforeunload`, form state and persistence.
**Alex:** "Write a proposal of what you recommend changing"
**Type:** fix proposal
**Effort:** L overall, but staged. Two steps land on this branch (S each, compiler-checked, no test changes). The rest are four independent follow-ups of S–M.

This is not a rewrite. `useArticleDraft` survives as a named export with the same
21-member return shape throughout; each step moves one concern out of its body into a
unit with a narrower contract. Every step is either checked by the compiler or by the
19 tests that already exist, and each is independently revertable.

## What is actually happening

`useArticleDraft.ts` currently owns six things:

| Concern | Lines |
|---|---|
| Load: channels + article, or eager create on `/new` | `:95–150` |
| Routing: `router.replace` on create, `router.push` after publish/delete | `:123`, `:322`, `:345` |
| Sweep: delete the draft on unmount if it looks untouched | `:43–54`, `:162–170` |
| Leave guard: `beforeunload` | `:208–215` |
| Form state: fields, the body ref, snapshot, dirty | `:16–28`, `:172–203` |
| Persistence: update / publish / delete + their flags and messages | `:259–350` |

Three artefacts fall out of the mixing:

1. **`latestRef.current.leaving`** (`:83–91`). A mutable "I am about to be unmounted"
   bit, written at three sites, read from a cleanup that by construction sees a stale
   snapshot. It exists only because the hook both decides to navigate and reacts to
   being unmounted. Nothing else in the codebase has this shape.
2. **`ArticleFormState.body`** (`:18`). A field that is wrong except in the instant
   after `snapshotForm()` (`:182–187`). The live body is `bodyRef.current` (`:78`).
   Three paths remember to snapshot; the comment at `:180–181` is doing a type's job.
3. **The 21-member return** (`:352–386`), which is what a component gets when its
   state hook has no seam to hand it a subset.

Findings I4 and I5 both live in this mixture — but be clear about the causation:

- **I5 is caused by it.** The hook navigates because the hook owns the create. A unit
  that only loads and creates would hand the new article back and let the page decide
  what a URL means; the "interactive page that is already navigating away" state
  could not be written.
- **I4 is not caused by it, only hidden by it.** The sweep's predicate would be wrong
  in any file. What the mixing costs is that the predicate is unreachable from a test
  without mounting React, so nobody enumerated its cases.

So: **neither finding is fixed by the decomposition.** Fix them first, as the two
targeted patches in `04-draft-deleted-mid-upload.md` and `05-new-route-typing-lost.md`.
The decomposition is what stops the next one being written.

## Proposed change

### Target decomposition

Six units plus the page, all under
`src/web-ui/src/app/projects/[slug]/articles/`.

**1. `articleDraftState.ts` — pure, no React, no network.**

```ts
export interface ArticleFormFields {
  title: string;
  channel_id: string;
  summary: string;
  listing_image_id: string | null;
  listing_crop: CropRect | null;
  listing_image_mode: ListingImageMode;
}

// Fields plus the body, which lives in the editor and only exists at snapshot
// time. The only producer is `useArticleForm().snapshot()`.
export type ArticleSavePayload = ArticleFormFields & { body: string };

export function fieldsFromArticle(article: Article): ArticleFormFields;
export function hasUnsavedChanges(
  article: Article,
  fields: ArticleFormFields,
  body: string,
): boolean;

export interface LeaveState {
  article: Article;
  fields: ArticleFormFields | null;
  body: string;
  arrivedEmpty: boolean;
  pendingUploads: number;
  uploadedImageIds: readonly string[];
}
export function shouldDiscardDraft(state: LeaveState): boolean;
```

**2. `useArticleForm.ts`** — owns `fields`, `bodyRef`, and nothing else.

```ts
function useArticleForm(article: Article | null): {
  fields: ArticleFormFields | null;
  updateFields(patch: Partial<ArticleFormFields>): void;
  handleBodyChange(markdown: string): void;
  snapshot(): ArticleSavePayload | null;
  hasUnsavedChanges(): boolean;
  reset(article: Article): void;
}
```

No network, no router, no article ownership beyond the last-saved copy it compares
against.

**3. `useArticleImages.ts`** — the upload registry from
`04-draft-deleted-mid-upload.md`, promoted to its own unit.

```ts
function useArticleImages(article: Article | null): {
  images: ProjectImage[];
  adoptImage(image: ProjectImage): void;       // wizard + inline upload
  beginUpload(): void;
  settleUpload(image: ProjectImage | null): void;
  pendingUploadsRef: RefObject<number>;        // read by the sweep
  uploadedImageIdsRef: RefObject<string[]>;    // read by the sweep
}
```

**4. `useArticleLoad.ts`** — channels + article, or create. Reports; does not navigate.

```ts
function useArticleLoad(options: {
  projectRef: string;
  articleId?: string;
  onCreated(article: Article): void;   // the page decides what to do with the URL
}): {
  channels: Channel[];
  article: Article | null;
  setArticle(next: Article | null): void;
  isLoading: boolean;
  error: string;
  arrivedEmptyRef: RefObject<boolean>;
}
```

`onCreated` is the seam that makes I5 unwritable: the unit has no `router`, so it
cannot render an interactive page onto a navigation it started.

**5. `useArticleMutations.ts`** — persistence only, returns results.

```ts
function useArticleMutations(projectRef: string, article: Article | null): {
  save(payload: ArticleSavePayload): Promise<Article | null>;
  publish(payload: ArticleSavePayload): Promise<Article | null>;
  remove(): Promise<boolean>;
  isSaving: boolean;
  isPublishing: boolean;
  isDeleting: boolean;
  error: string;
  setError(message: string): void;
  successMessage: string;
}
```

No `router.push`. `publish` returns the published `Article` (the endpoint already
does — `lib/api/articles.ts:58–66` returns `Promise<Article>`; the hook currently
discards it at `:320`). This is also where B5's error narrowing belongs: one
`describeApiError(err)` helper replacing the three
`err instanceof Error ? err.message : "…"` sites at `:141`, `:287`, `:347`.

**6. `useLeaveGuard.ts`** — the `beforeunload` effect (`:208–215`) plus the
`confirmLeave()` the breadcrumb calls, so the prompt string lives once rather than in
`ArticleAuthoringPage.tsx:28` and the browser dialog.

**7. `useArticleDraft.ts`** — assembly. Composes 2–6, keeps its current return shape
so no consumer or test moves, and shrinks to roughly 80 lines of wiring.

**8. `ArticleAuthoringPage.tsx`** — gains the three routing decisions: the URL swap on
create (`onCreated`), `router.push` after a successful publish, `router.push` after a
successful delete. It is the unit that knows what navigation means.

### How `leaving` dies

Three writers today:

- `:122`, the create swap — gone once `05-new-route-typing-lost.md` option (c) lands.
  A `history.replaceState` does not unmount anything.
- `:321`, publish — becomes unnecessary once `publish` writes its response back:
  `setArticle(published)` makes `article.state === "published"`, and
  `shouldDiscardDraft` returns false on a published article (first guard in
  `04-draft-deleted-mid-upload.md`).
- `:344`, delete — becomes unnecessary with `setArticle(null)` after a successful
  delete; the sweep already no-ops on `!current` (`:166`).

So `leaving` and the whole `latestRef` triple are deleted by two `setArticle` calls
plus the I5 fix. That is worth noting: it is not a payoff that waits for the
refactor, it is available as soon as the two bug fixes land.

### The `body` trap field, concretely

Today `ArticleFormState.body` (`:18`) is stale between snapshots and the type says
nothing. The fix is that the type of the thing you can persist is *not producible*
from form state alone:

- `ArticleFormFields` has no `body`.
- `ArticleSavePayload = ArticleFormFields & { body: string }`.
- `persistDraft`, `save` and `publish` take `ArticleSavePayload`.
- The only function that returns one is `snapshot()`, which reads `bodyRef.current`.

Passing `fields` where a payload is expected is then a missing-property error, not a
silent stale write. The "fourth path that forgets to snapshot" stops compiling.

Consumer impact is one line: `ArticleAuthoringPage.tsx:264` reads `form.body` for
`initialMarkdown` and becomes `article.body`. Verified safe — `form.body` and
`article.body` are equal at mount and after every save, and MDXEditor takes the prop
as `initialMarkdown` into `corePlugin` at init only; `corePlugin.update`
(`node_modules/@mdxeditor/editor/dist/plugins/core/index.js:594–609`) does not
republish it, so changing that prop after mount has no effect either way. It is the
only `form.body` read in the codebase.

### What each split actually eliminates

| Split | I4 | I5 | Other |
|---|---|---|---|
| `useArticleLoad` with `onCreated` | — | **eliminates** — the unit cannot navigate, so it cannot render onto a navigation | removes 1 of 3 `leaving` writers |
| `useArticleImages` | **eliminates**, given the guard in doc 04 | — | fixes the wizard not seeing inline uploads |
| `shouldDiscardDraft` as a pure function | makes it *testable*, does not fix it | — | 4 sweep cases become table tests |
| Routing to the page | — | supports the fix, does not make it | removes the other 2 `leaving` writers |
| `ArticleSavePayload` | — | — | kills the trap field |
| `useArticleMutations` | — | — | one place for B5's error narrowing |

Read that as: the splits pay for themselves in the trap field, `leaving`, and
testability. The two bugs are paid for by the two targeted patches.

### Migration order

**Lands on this branch:**

- **Step 0.** The two targeted fixes (`04-draft-deleted-mid-upload.md`,
  `05-new-route-typing-lost.md`). Independent of each other and of everything below.
- **Step 1.** `body` off the form; introduce `ArticleFormFields` /
  `ArticleSavePayload`. ~40 lines, entirely mechanical, verified by `tsc --noEmit`.
  One consumer change (`ArticleAuthoringPage.tsx:264`). No test changes.
- **Step 2.** Extract `articleDraftState.ts` — `fieldsFromArticle`,
  `hasUnsavedChanges`, `shouldDiscardDraft`. Pure moves; the hook calls them. Adds a
  new pure test file; existing tests untouched.

Steps 1 and 2 are worth taking now because they are where the next bug would
otherwise be written, and because Step 2 is where the doc 04 sweep cases get proper
tests.

**Follow-ups, in this order:**

- **A.** `useArticleForm` + `useArticleImages`. `useArticleDraft` keeps its return
  shape, so the 19 tests stay green as the acceptance criterion.
- **B.** `useArticleMutations` + `describeApiError`. Land the missing `publish()` /
  `remove()` tests here — the frontend review's coverage gap list — because this is
  when their error handling changes.
- **C.** Move `router.push` into `ArticleAuthoringPage`; delete `leaving` and
  `latestRef`. Also the point at which `useArticleDraft`'s return can shrink, since
  the page stops needing the members it only forwarded.
- **D.** *(needs a decision, not just work)* Drop eager creation — create the article
  on first upload or first save. Removes the sweep, `creatingRef`, and I4's whole
  class. Costs: `ArticleEditor` and `ListingImageDialog` take
  `ensureArticleId: () => Promise<string>` instead of `articleId: string`;
  `persistDraft` branches create/update; `article` is null for part of the page's
  life. See option (b) in `05-new-route-typing-lost.md`. Pair it with a server-side
  reaper for provisional drafts, which is the only thing that handles a killed tab.

Nothing after Step 2 is required for the branch to ship.

## Tests

`use-article-draft.test.tsx` has 19 tests: `opening /new` 3, `a load that fails` 1,
`choosing a listing image` 4, `the untouched-draft sweep` 4, `saving` 3,
`unsaved changes` 4.

- **Steps 1–2:** none change. No test reads `form.body`; the sweep and dirty tests go
  through the hook's public surface, which is unchanged.
- **Doc 05's fix:** two rewrites — `:167` asserts a `history.replaceState` spy instead
  of the `replace` mock, `:186` inverts to "sweeps the draft when the author leaves
  `/new` without writing anything". Detailed in that document.
- **Doc 04's fix:** four new cases. Three of them (published, arrived-with-content,
  settled-failure) belong in the new `article-draft-state.test.ts` as calls to
  `shouldDiscardDraft` with a `LeaveState` literal — no mounting, no async. Only
  "keeps a draft while an inline upload is in flight" needs the React harness.
- **Follow-ups A–C:** the contract is that the 19 (then 21) tests stay green
  unmodified. If a step needs a test edited, the step moved behaviour it should not
  have moved — that is the signal to split it further, not to edit the test.
- **Gaps to close on the way through** (all from the frontend review's own list):
  `publish()` and `remove()` are entirely untested including the 422 `detail`
  extraction at `:324–329`; `ArticleAuthoringPage.handleTabClick` (`:131`) has no
  coverage at all; `hooks/useImageUpload.ts` has none. B is the natural home for the
  first two.

## Risks and what this does not cover

- **Churn on a branch that is trying to land.** This is why only Steps 1 and 2 are
  proposed for now: both are compiler-verified and neither changes runtime behaviour.
  Everything with behavioural risk is a follow-up.
- **Hook-count inflation.** Six units where there was one is a real cost if the
  composite is not kept. `useArticleDraft` must remain the single thing
  `ArticleAuthoringPage` imports; if consumers start reaching for the sub-hooks
  directly, the seam becomes a public API and the freedom to re-cut it is gone.
- **`useArticleImages` and `useArticleLoad` both want `setArticle`.** The article
  object is genuinely shared state: the load writes it, mutations replace it, image
  adoption patches it. Whichever unit ends up owning it, the other two take a setter,
  and that is a seam that can rot. Keep ownership in `useArticleLoad` and pass the
  setter down explicitly rather than introducing a context.
- **Step D is a product decision.** "No draft exists until you write something" changes
  what the author's article list shows and when. Do not let it arrive as a refactor
  side effect.
- **Does not address I6** (the implicit save on the listing tab pushing unsaved edits
  live). That needs an unpublished-revision concept and is correctly headed for
  follow-ups.
- **Does not address B4** (a slow save reverting a listing image chosen while it was in
  flight). `persistDraft`'s response merge at `:275–284` needs a request-generation
  counter regardless of where the code lives; the refactor neither helps nor hurts.
