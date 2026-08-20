# Design: guard unsaved article edits

## Context

See [`proposal.md`](proposal.md) for the motivation. The mechanics that shape
every decision below:

- The body is uncontrolled. MDXEditor owns it; the page reads it out of a ref at
  save time (`articleDraftState.ts:20-25`). There is no state update to hang a
  router block on, and no server copy until the author presses Save.
- `hasUnsavedChanges` (`articleDraftState.ts:42`) already answers "would leaving
  now lose something", comparing body and every editable field against the last
  article the server returned. `useArticleForm` wraps it as `isDirty`
  (`useArticleForm.ts:62`), and `useArticleDraft` hands that to `useLeaveGuard`
  (`useArticleDraft.ts:129`). The predicate is settled; only the set of exits it
  is consulted on is wrong.
- The App Router has no navigation-blocking API. The Pages Router had
  `router.events` and `routeChangeStart` with a throwable abort; `next/navigation`
  exposes nothing equivalent, and `<Link>` navigation is a plain click handled in
  React. There is no supported seam between "the author clicked" and "the route
  changed" other than the click itself.
- The links that matter are not the page's. `layout.tsx:73-78` renders
  `Navigation` and `Footer` as siblings of `{children}`, so they mount above the
  page in the tree and know nothing about it.

## Goals / Non-Goals

**Goals:**

- Leaving the authoring page with unsaved work prompts, whichever link in the
  document was clicked.
- Zero changes outside `src/app/projects/[slug]/articles/`. The chrome stays
  ignorant of the editor.
- Nothing prompts when there is nothing to lose, and nothing prompts on the
  exits the author took on purpose.

**Non-Goals:**

- Covering Back and Forward, logout, or navigation another component performs
  in code. All three are recorded as known limitations in the proposal rather
  than promised here.
- Replacing `window.confirm` with a designed dialog.
- Autosave or a local draft cache.

## Decisions

### A capture-phase listener on `window`, not per-link opt-in

The alternative is what exists today: each link calls `confirmLeave()` in its
`onClick`. It works, and it has already failed — one link out of a dozen adopted
it, and the dozen live in files the editor has no business editing. Any new link
anywhere in the chrome would be a new leak.

Capture phase matters, and so does the target being `window` rather than
`document`. The App Router hydrates the React root into `document`, and React
attaches its whole synthetic event system as a single listener on that root
container — so a `document` capture listener registered after hydration runs
*after* React has dispatched `<Link>`'s own `onClick`, which has already
`preventDefault`ed and called `router.push`. `window` sits above `document` in
the capture path and therefore runs first regardless of registration order,
which is what lets `preventDefault()` stop the navigation instead of racing it.

*Alternative considered:* patching `history.pushState` / monkeypatching the
router. It catches programmatic navigation too, which the click listener misses,
but it fires after the decision to navigate has been taken — there is nothing
left to cancel, only a "navigate back" to fake, and faking it leaves the editor
remounted with the body gone. Rejected.

### The listener lives as long as the page, and asks about dirtiness inside

Registering only while dirty would keep a global listener off the document for
the clean case, but the dirty state is derived from a ref the editor writes
without re-rendering — there is no render to hang the registration on, so it
would have to be polled or the effect re-run on every keystroke. One listener
for the page's lifetime, calling `isDirty()` as its first act, costs a set
membership test per click and cannot be stale. It also unregisters on unmount in
the same effect cleanup as `beforeunload`, so there is one lifetime to reason
about rather than two.

### What counts as "leaving"

The handler resolves the clicked element to its closest `a[href]` and only
prompts when following it would take the browsing context off the current path.
Everything below stays silent because none of it loses work:

- No anchor in the click's ancestry — a button, the editor toolbar, a tab.
- An anchor whose resolved `pathname` **and** `search` equal the current one,
  which covers bare `#` and in-page section links. Comparing the path alone
  would wave through a query-string change; comparing the whole URL would prompt
  on a fragment.
- A modified click — `ctrl`/`cmd`/`shift`/`alt` — or a non-primary button, and a
  `target` other than `_self`: the page stays open, so nothing is lost.
- A `download` link, and a `mailto:` / `tel:` / `sms:` / `javascript:` href.
  These hand the click to something that is not the browsing context.
- A default-prevented click: something upstream already handled it.
- A link inside a `contenteditable` — one the author wrote into the body.
  Clicking it puts the caret in it rather than following it, so prompting would
  fire on an ordinary edit.

### The breadcrumb stops guarding itself

`confirmLeave` existed so one link could opt in. Now that no link has to, a
second guard on that one link is two prompts to keep in step and one more way
for them to diverge. The callback goes with it, so `useLeaveGuard` is called for
its effect alone and there is exactly one place that decides whether leaving is
allowed.

### Back and Forward: a sentinel was built, measured and rejected

A `popstate` handler on its own is too late — the entry has already moved, and
the only recovery is pushing the author forward again, by which point the editor
has unmounted and taken the body with it. The way round that is a sentinel: push
a duplicate history entry for the authoring URL, so the first Back press lands
back on the same page and `popstate` gets to ask before anything is lost. It was
implemented and driven in a real browser, and it does not ship.

`pushState` discards every forward entry. The sentinel armed on mount, so merely
opening the editor destroyed the browser's Forward stack — for an author who was
only reading, who then found Forward dead on a page they had not edited. That is
a worse bug than the one being fixed, and it is not a detail of the
implementation: arming is what breaks it. Two smaller holes came with it. A
multi-step Back — press-and-hold, or several presses faster than the handler
settles — skips past the sentinel and off the page unasked. And because the
entry outlives an unmount that races the pop, the guard could leave a stray
entry on an unrelated page.

So Back and Forward are **not** guarded. Recorded here rather than deleted so
the next person does not rebuild it and find the same wall.

If someone does revisit it: arm on the first edit, not on mount. A reader never
pays for the guard then, and an author who has started typing has usually not
built a Forward stack worth keeping. The multi-step-Back hole would remain, and
there is no version of a sentinel that closes it — the durable answer for Back
is autosave, not interception.

### `window.confirm`, not a dialog component

Cancelling a click has to happen in the handler, synchronously. A React dialog
resolves a promise on a later tick, by which point the navigation has committed.
The page already confirms deletion with `window.confirm`
(`ArticleAuthoringPage.tsx:121`), so the ugliness is at least consistent, and
the prompt string stays in `useLeaveGuard` so `beforeunload` and the click path
cannot drift apart.

`beforeunload` cannot show custom text at all — every browser replaced it with a
fixed string years ago — so the two paths were never going to read identically.

### Publish and delete are silent by construction

Both navigate with `router.push` (`useArticleDraft.ts:169,176`), not an anchor,
so the listener never sees them. That is luck rather than design, and the spec
pins it as a requirement so a later refactor to a `<Link>` cannot quietly start
prompting the author after they pressed Publish.

Publishing also saves first, which would leave the page clean; deleting does
not, and a deleted article's unsaved body is exactly the work the author just
asked to throw away.

## Risks / Trade-offs

- **A global capture listener can swallow a click it should not.** → It only
  ever acts on anchors leading off the current path, and only while dirty; every
  other click falls through untouched. Tests cover the fall-through cases
  explicitly, not just the prompt case.
- **`window.confirm` is blocking and ugly, and some environments suppress it.**
  → Accepted for the reason above. A suppressed `confirm` returns `false` in
  most browsers, which fails closed: the author stays on the page.
- **A declined click still runs the link's own `onClick`.** Not calling
  `stopPropagation` is what lets the drawer and the user menu close behind the
  dialog, and it has a cost: clicking a notification row in the bell popover and
  then declining still fires `markArticleRead` and closes the popover
  (`NotificationsBell.tsx:99-111`). The author keeps their work, which is the
  point, but the notification is marked read on a navigation that never
  happened. Accepted — the alternative is menus stuck open behind a cancelled
  click, on every link in the chrome.
- **Three exits stay open**: Back and Forward, a toast click, and log out. None
  is a link the interceptor can see, and the sentinel that would have covered
  the first is rejected above. → Named in the proposal under Known limitations
  and in the spec's requirement, and deliberately not written as a SHALL.
  Guarding the toast or logout means the component asking the editor for
  permission, which is the opt-in pattern this change removes; the durable
  answer for all three is autosave.
- **Two guards say slightly different things.** `beforeunload` shows the
  browser's fixed wording, the click path shows ours. → Unavoidable; the shared
  constant keeps ours in one place.
- **The full flow is awkward to drive end to end.** It needs a logged-in
  author, a seeded project and a draft, and login is rate-limited to 5 requests
  per minute per IP (`api/rate_limit.py`). → The click and unload paths are
  covered by vitest, and the interception mechanism by `e2e/leave-guard.spec.ts`
  in a real browser. The manual passes against the authenticated editor are
  still outstanding — see [`tasks.md`](tasks.md).

## Migration Plan

None. Frontend-only, no schema, no contract. Deploying is shipping the build;
rolling back is reverting it.

## Open Questions

- Whether to autosave the body. It would close the three limitations above,
  which no click or history guard can reach, and make the rest of this defence
  in depth rather than the only defence. Out of scope here; the argument for it
  is stronger after this change than before, because what remains unguarded is
  now exactly the set of exits no interception can see.
