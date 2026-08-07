# 05. Text typed immediately after `/new` is discarded

**Finding:** I5 — `/new` renders a fully interactive editor while it is already navigating to `/edit/<id>`; the remount refetches an empty article and the typed text goes with it.
**Alex:** "what do you suggest?"
**Type:** fix proposal
**Effort:** S for the recommended option — one statement in `useArticleDraft.ts`, one derived label in `ArticleAuthoringPage.tsx`, two existing tests rewritten.

## What is actually happening

`useArticleDraft.ts:95–150`, the create branch:

```ts
loaded = await api.articles.create(projectRef, { ... });      // :113
if (cancelled) return;
latestRef.current.leaving = true;                             // :122
router.replace(`/projects/${projectRef}/articles/edit/${loaded.id}`);  // :123
...
setArticle(loaded);                                           // :127
bodyRef.current = loaded.body;
setForm({ title: loaded.title, body: loaded.body, ... });     // :129
setIsLoading(false);                                          // :138
```

`router.replace` starts a transition and returns. Nothing awaits it. The four lines
after it run in the same tick, so `ArticleAuthoringPage` drops out of the skeleton
branch at `:63` and renders the title input (`:221`), the channel dropdown and the
body editor — on a page that is already navigating away.

`/new/page.tsx` and `/edit/[articleId]/page.tsx` are distinct route segments. Both
are server components that `await getProjectOr404(slug)`. When the RSC payload for
`/edit/<id>` lands, React unmounts the `/new` tree and mounts a fresh
`ArticleAuthoringPage`, which runs a fresh `useArticleDraft`, which calls
`api.articles.get(projectRef, articleId)` and gets back the article as the server
holds it — `title: ""`, `body: ""`.

Everything the author typed lived in `form` and `bodyRef` inside the unmounted hook.
It is gone. No prompt: `isDirty()` is on the old instance, and the transition is not
a link click, so `ArticleAuthoringPage.tsx:154` never runs.

The window is the RSC fetch plus a `getProjectOr404` server call. Locally it is
imperceptible; on a cold backend or a bad connection it is seconds.

The premise behind the eager creation is sound and is stated at `:104–106`: an
upload cannot name an article that does not exist. `ArticleEditor` takes
`articleId: string` (non-optional, `:40`) and `api.articles.getImageUploadUrl` is
addressed by article. `ListingImageDialog` (`:39`) has the same requirement. So the
id genuinely must exist before either surface is usable. The bug is not the eager
create; it is that the URL swap is a route change.

## Proposed change

### Option (a) — keep the editor loading until the navigation lands

Skip the state writes on the create path and let the `/edit` mount do the rendering:

```ts
latestRef.current.leaving = true;
router.replace(`/projects/${projectRef}/articles/edit/${loaded.id}`);
return;   // the /edit mount loads and renders; this one is on its way out
```

Nothing can be typed, so nothing can be lost. Roughly three lines.

Costs: the author looks at a skeleton for the length of the RSC fetch, which is the
exact interval that today feels fast. If the navigation stalls — offline, a failing
RSC fetch — the page is a skeleton with no error and no way out; Next 16 falls back
to a hard navigation on RSC fetch failure, so this is unlikely rather than
impossible, but there is no timeout. It also keeps the double fetch (create then
get) and the double `getProjectOr404`.

### Option (b) — stop creating the draft eagerly; create on first upload

Defer `api.articles.create` until something actually needs an article id.

What it touches: `ArticleEditor` and `ListingImageDialog` both take
`articleId: string` today and would take `ensureArticleId: () => Promise<string>`;
`persistDraft` (`:259`) branches create-vs-update; `article` is null for the first
part of the page's life, so `ArticleAuthoringPage.tsx:98` ("Couldn't open this
article") has to stop treating a null article as failure; `remove()` (`:339`) no-ops;
the implicit save on the listing tab (`:131`) has to create.

What it buys: no empty drafts ever exist, so the whole sweep — `isUntouched`, the
cleanup at `:162`, `creatingRef`, and finding I4's entire class — disappears.

Why it does not win here: **it does not fix I5.** The first upload still produces an
article id, and that id still has to reach the URL, so the swap problem is deferred,
not removed — you end up needing option (c) anyway, just less often. And it is the
largest change of the four, on a branch that is trying to land.

### Option (c) — swap the URL without a route change *(recommended)*

Replace the `router.replace` with a native history call:

```ts
loaded = await api.articles.create(projectRef, { ... });
if (cancelled) return;
// A native replaceState rather than router.replace: /new and /edit are distinct
// route segments, so a router navigation would unmount this page and the /edit
// mount would refetch an article that is still empty — losing anything typed in
// the meantime. The App Router picks up history.replaceState, so the URL is
// correct for a reload or a copy-paste while the tree stays mounted.
window.history.replaceState(
  null,
  "",
  `/projects/${projectRef}/articles/edit/${loaded.id}`,
);
```

`latestRef.current.leaving = true` is deleted from this path — there is no unmount to
suppress, and leaving it set would disable the sweep for the whole session.

One mount now owns the draft from creation to departure. Nothing is refetched,
nothing is typed into a doomed component, and the `/edit` page component simply never
runs in this session (it runs correctly on a reload or a direct visit).

Next 16.1.6 supports `window.history.pushState`/`replaceState` and syncs
`usePathname`/`useSearchParams` from them; this is the documented escape hatch for
exactly this case. `replaceState` replaces the `/new` entry, so Back behaves as it
does today with `router.replace`.

One cosmetic follow-on: `ArticleAuthoringPage.tsx:60–61` derives the breadcrumb label
from the `articleId` prop, which stays undefined for the life of the mount, so it
would read "New article" forever instead of flipping to "Edit article" after the
swap. Derive it from the draft instead:

```ts
const mode = draft.article ? "Edit article" : "New article";
```

### Option (d) — pass the loaded article through so `/edit` does not refetch

Rejected, and the premise is wrong: what is lost is not the fetched article, it is
the typed text held in the unmounted component's `form` state and `bodyRef`. Handing
the `/edit` mount a pre-loaded article removes one GET and loses the typing exactly
as before. To make (d) work you would have to carry the *draft state* across the
route change — a module-level cache or context above both segments — which is a
worse version of (c): the same "don't remount" goal, achieved by rebuilding the state
you just threw away.

### Recommendation

**(c) now, (b) later.**

(c) is the smallest change that actually removes the loss, it keeps the reason the
eager create exists intact (the id is available before the editor mounts, as today),
and it improves the I4 fix: with a single mount owning the draft's whole life, the
`arrivedEmpty` flag proposed in `04-draft-deleted-mid-upload.md` becomes precisely
"this session created this draft", which is what the sweep was always meant to mean.
It also removes the first of `leaving`'s three call sites — see
`10-use-article-draft-refactor.md` for how the other two go.

(a) is the fallback if the history swap turns out to fight the router in practice.
It is strictly worse — same time to interactive, less of it usable — but it is
correct and it is three lines.

(b) is the right end state and belongs in the refactor sequence, not this branch.

## Tests

`use-article-draft.test.tsx` — the `"opening /new"` block (`:166–193`):

- `:167` `creates a draft up front and swaps the URL to its edit route` — keep the
  name, change the assertion from the `replace` mock to a
  `vi.spyOn(window.history, "replaceState")`, asserting the third argument.
  jsdom implements `replaceState`.
- `:186` `leaves the draft it is navigating to alone` — no longer meaningful; there
  is no navigation and no unmount. Replace with
  `sweeps the draft when the author leaves /new without writing anything`, asserting
  `articles.delete` *is* called on unmount. That is the same net behaviour as today
  (the `/edit` mount does it), performed by one mount instead of two.
- `:178` `creates one draft per visit when effects run twice` — unchanged.
- New: `keeps text typed before the URL swap` — mount without `articleId`, call
  `updateForm({ title: "A headline" })`, assert `draft().form?.title` is still
  `"A headline"` and that `articles.get` was never called. This is the regression
  test for the finding.

Playwright: no existing spec covers `/new` at all (both e2e specs start from an
already-created article). Add to `e2e/article-images.spec.ts` or a new spec: open
`/new` with the article-create response delayed, type a title as soon as the field
appears, wait for the URL to become `/edit/<id>`, assert the title input still holds
the typed text.

## Risks and what this does not cover

- **Router/tree mismatch.** The URL says `/edit/<id>` while the mounted segment is
  `/new`. Nothing in this app reads route params on that page — `ArticleAuthoringPage`
  takes `project` and `articleId` as props from the server component, not from
  `useParams` — but a future change that adds `/edit`-only behaviour to
  `edit/[articleId]/page.tsx` would silently not apply in the create session. Worth a
  comment on that page saying so.
- **`isEditing` stays false for the session.** It is used only in the load effect's
  deps and for the breadcrumb label. The label fix above covers the visible half;
  grep for any new use before landing.
- **A hard reload mid-typing still loses the text.** `beforeunload` (`:208–215`) warns,
  which is all it can do. Unchanged by this fix.
- **The double fetch stays.** `/new` does `getProjectOr404` server-side and
  `channels.list` + `articles.create` client-side. (c) removes the *second*
  `getProjectOr404` and the redundant `articles.get` that the remount performs today,
  which is a small win, but the create-on-mount round trip remains — only option (b)
  removes that.
- **Does not fix I4.** The sweep still needs the upload guard. The two changes are
  independent and can land in either order.
