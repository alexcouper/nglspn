# Tasks: guard unsaved article edits

## 1. Extend the leave guard to navigation the page does not own

- [x] 1.1 In `src/web-ui/src/app/projects/[slug]/articles/useLeaveGuard.ts`, add a
  `click` listener on `window` in the **capture** phase, in the same effect as
  the existing `beforeunload` listener and torn down with it.
- [x] 1.2 Return immediately when the event's default is already prevented or
  `isDirty()` is false, so a clean page and an already-handled click cost one
  call.
- [x] 1.3 Resolve `event.target` to its closest `a[href]` and return when there is
  none.
- [x] 1.4 Add an `isLeavingClick` predicate covering the cases that keep the
  author on the page: a non-primary button; `ctrlKey` / `metaKey` / `shiftKey` /
  `altKey`; a `target` other than `_self`; a `download` attribute; a `mailto:`,
  `tel:`, `sms:` or `javascript:` scheme; an href that fails to parse; and a
  destination whose `pathname` and `search` both match the current URL's.
- [x] 1.5 Exclude links inside a `contenteditable`. Clicking one the author wrote
  into the body puts the caret in it rather than following it, so prompting there
  would fire on an ordinary edit. Match the attribute, not `isContentEditable`,
  which jsdom does not compute.
- [x] 1.6 Otherwise prompt with the existing `LEAVE_PROMPT` via `window.confirm`,
  and on a decline call `preventDefault()` — and **not** `stopPropagation()`.
  `Link` runs the anchor's own `onClick` before bailing on `defaultPrevented`, so
  cancelling the default stops the navigation while the drawer and the user menu
  still close behind the dialog.
- [x] 1.7 Set `event.returnValue = ""` in the `beforeunload` handler alongside the
  `preventDefault()`, for the older Safari spelling.
- [x] 1.8 Drop the returned `confirmLeave` callback, the breadcrumb's `onClick`
  guard in `ArticleAuthoringPage.tsx`, and `confirmLeave` from the object
  `useArticleDraft` returns. One guard, in one place.
- [x] 1.9 Record in a comment why the listener sits on `window` and not
  `document`: React attaches its synthetic event system to the hydration root on
  `document`, so a `document` capture listener would run after `<Link>`'s own
  `onClick` had already called `router.push`.

## 2. Tests

- [x] 2.1 Add `src/web-ui/src/app/projects/[slug]/articles/use-leave-guard.test.tsx`,
  rendering the hook with a controllable `isDirty` and a stubbed
  `window.confirm`.
- [x] 2.2 Dirty, a link off the current path: declining cancels the navigation,
  confirming lets it through.
- [x] 2.3 A declined click still reaches the link's own handlers, which is what
  keeps the menus closing.
- [x] 2.4 A click on an element nested inside the link still prompts; a click that
  hit no link at all does not; an already-cancelled click is left alone.
- [x] 2.5 Clean draft: never asks.
- [x] 2.6 The silent cases from 1.4 and 1.5, one assertion each — each modifier
  key, a non-primary button, another tab, a download, a `mailto:`, a bare hash, a
  section link on this page, a link inside the body.
- [x] 2.7 `beforeunload` warns while dirty and stays quiet while clean.
- [x] 2.8 After unmount, neither clicks nor unloads are guarded.
- [x] 2.9 Add `src/web-ui/e2e/leave-guard.spec.ts`, checking in a real browser
  that `preventDefault` alone cancels an App Router `Link`. It transcribes the
  interception onto a public page rather than driving the authenticated editor.
  Keep it out of CI, as the rest of `e2e/` is.

## 3. Verify

- [x] 3.1 `make lint` and `make test` in `src/web-ui/` — lint clean, full vitest
  suite passing.
- [x] 3.2 `npx playwright test e2e/leave-guard.spec.ts` — both tests pass in
  Chrome.
- [ ] 3.3 `make build-app` and `make extra-tests` in `src/web-ui/` — the bundle
  budgets are per route and this adds code to the authoring route.
- [ ] 3.4 **Blocked — nobody has driven the real editor in a browser.** The
  credentials in `.env.claude` 401 against the local backend, and only one dev
  account has `full_edit`, so none of the manual passes below has been run. The
  shipped hook's own behaviour rests on the unit tests until someone with a
  working authoring account works through them:
  - the reported bug: open a draft, type into the body, click **My Projects** in
    the header; the prompt appears, declining keeps the typed text, accepting
    leaves;
  - the quiet cases: with unsaved text, switch editor tabs and open a link in a
    new tab — neither prompts; save, then click a header link — no prompt;
  - the deliberate exits: publish an article, and separately delete one, and
    neither shows a leave prompt on the way to the project page;
  - hard navigation: with unsaved text, reload the tab and the browser's own
    warning still fires;
  - the three known limitations still read true — Back, a toast click and **Log
    out** all leave without a prompt — so the proposal describes what ships.
