# Guard unsaved article edits

## Why

An author writes half an article, clicks **My Projects** in the header, and the
text is gone. No prompt, no draft, nothing to go back to. That is
[issue #84](https://github.com/alexcouper/nglspn/issues/84).

The body is the part that hurts. MDXEditor holds it uncontrolled in a ref
(`articleDraftState.ts:20`), so between saves it exists only in the page's
memory — leaving the page is deleting it. The form fields go the same way.

A guard exists but covers one door out of many. `useLeaveGuard`
(`src/app/projects/[slug]/articles/useLeaveGuard.ts`) registers a `beforeunload`
listener, which browsers fire only for browser-level navigation, and returns a
`confirmLeave()` that in-app links are expected to call for themselves. Exactly
one link calls it: the breadcrumb, at `ArticleAuthoringPage.tsx:152`.

Everything else that navigates is rendered by the root layout as a sibling of
the page — `Navigation` and `Footer` in `src/app/layout.tsx:73-78`, and inside
`Navigation` the logo, Projects, Competitions, My Projects, the `UserMenu`
entries and the `NotificationsBell` links. The page cannot reach into them to
opt them in, and it should not have to: a guard that depends on every future
link in the app remembering to ask is a guard that decays.

## What Changes

- **The authoring page guards itself against navigation it does not own.** A
  capture-phase `click` listener on `window` inspects the anchor a click
  resolves to. If the draft is dirty and following that anchor would leave the
  current path, the author is asked to confirm; declining cancels the click and
  leaves them where they were with the work intact.
- **The prompt is `window.confirm`**, the same mechanism as the page's existing
  delete confirmation (`ArticleAuthoringPage.tsx:121`). A custom dialog cannot
  answer synchronously, and a click can only be cancelled synchronously.
- **`beforeunload` stays** as the cover for closing the tab, reloading, or
  typing a new URL. It is the browser's own dialog and nothing else can produce
  it.
- **The breadcrumb's own `confirmLeave()` call goes, and so does the callback
  the hook returned for it.** With the window listener in place it is a second
  guard on one link out of many — two prompts to keep in step for no coverage
  the interceptor does not already give.
- **Clicks that never leave the page stay silent**: a modified or non-primary
  click, `target` other than `_self`, a `download` link, a `mailto:` / `tel:` /
  `sms:` / `javascript:` href, any href resolving to the current path and
  query, and a link the author wrote into the body, where a click puts the caret
  in it rather than following it.
- **Deliberate exits stay silent.** Publishing and deleting both `router.push`
  to the project page (`useArticleDraft.ts:169,176`); neither is an anchor
  click, so neither reaches the listener, and neither should prompt.

Not breaking: no API, schema, route or contract change. `backend-openapi.json`
is untouched, and no backend file changes.

### Known limitations

Three exits stay unguarded. Recording them here rather than writing a
requirement the code does not meet:

- **Back and Forward.** A history sentinel — a duplicate entry pushed while the
  draft is dirty, so the first Back press lands back on the authoring page and
  `popstate` can ask — was built and driven in a real browser, and rejected.
  `pushState` discards all forward entries and the sentinel armed on mount, so
  merely opening the editor destroyed the Forward stack of every visitor,
  including one who only read the page. It also missed a multi-step Back and
  could leave a stray entry on an unrelated page. [`design.md`](design.md)
  keeps the full reasoning, and the one avenue worth trying if anyone revisits
  it. Unsaved work is still lost this way.
- **Clicking a notification in the toaster.** `NotificationToaster.tsx:36`
  navigates with `router.push`, and the toast body is a `<div onClick>` — there
  is no anchor for the click interceptor to resolve. Guarding it means the
  toaster asking the editor, which is the per-component opt-in this change
  exists to get away from. Unsaved work is still lost this way.
- **Log out from the user menu.** `logout()` (`contexts/auth.tsx:72`) clears the
  tokens and the user without navigating; `useRequireAuth` in
  `ArticleAuthoringRoute` then redirects, unmounting the editor. A button, not a
  link, so nothing here sees it either.

### Explicitly out of scope

- **Autosave, or persisting the body to `localStorage`.** Either would make
  most of this unnecessary and both are larger changes with their own failure
  modes (a draft written to the server the author never asked to save; a local
  copy that goes stale against a save made in another tab). Not ruled out
  later; not what #84 asks for.
- **A styled confirmation dialog.** Wanted eventually, blocked by the
  synchronous-cancel constraint above.

## Capabilities

### Modified Capabilities

- `articles`: a new requirement, alongside **Authoring endpoint and entry
  point**, that unsaved work survives an attempt to leave the authoring page by
  any route the page can observe — including navigation started by the global
  site chrome the page does not own.

## Impact

**Frontend** (`src/web-ui/`), all under `src/app/projects/[slug]/articles/`
except the e2e spec:

- `useLeaveGuard.ts` — gains the window-level click interceptor next to the
  existing `beforeunload` listener, and stops returning `confirmLeave`.
- `useArticleDraft.ts` — calls the hook for its effect only; `confirmLeave`
  leaves the returned draft object.
- `ArticleAuthoringPage.tsx` — the breadcrumb's `onClick` guard goes.
- `use-leave-guard.test.tsx` — new, covering the interceptor and
  `beforeunload`.
- `e2e/leave-guard.spec.ts` — new. It transcribes the interception mechanism
  onto a public page and checks it in a real browser rather than driving the
  authenticated editor, so the shipped hook's own behaviour is covered by the
  unit tests only.

**Not affected**: `Navigation.tsx`, `Footer.tsx`, `layout.tsx` and every other
component outside the articles directory — the point of putting the listener on
`window` is that the chrome needs no changes. Backend: none.
