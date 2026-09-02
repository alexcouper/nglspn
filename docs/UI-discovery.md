# UI review — discovery notes

Running notes from a maintainability review of `src/web-ui`. Working file, not a
finished doc: when it settles, the keepers move to `docs/<date>-<topic>.md` and
this goes away.

Scope asked for: **shared-component refactors**, **documentation that is too long
or argues design decisions**, **security implications**. Not a bug hunt.

## How I'm conducting the review

Seven passes, each producing findings with `path:line` anchors:

1. **Map the layers** — routing tree, server fetch (`lib/api/server.ts`) vs client
   fetch (`lib/api/*`), contexts, hooks. Establish what the intended architecture
   is before judging drift from it.
2. **Duplication sweep** — near-identical components across route trees
   (`app/old/**` vs `app/projects/**`, the several `*Dialog.tsx`, two
   `HorizontalScroll`), repeated Tailwind clusters, copy-pasted loading/error/empty
   states. Candidates for extraction into `src/components/`.
3. **Dead / superseded code** — `app/old/**`, unreferenced components, routes with
   no link into them. Deleting beats refactoring.
4. **Prose in the code** — comment blocks that argue a past design decision rather
   than explain the line. Repo style is terse; long rationale belongs in `docs/`.
5. **Security** — token storage, XSS surface (`rehype-raw` + `sanitize-schema.ts`,
   any `dangerouslySetInnerHTML`), redirect handling, `target="_blank"`,
   `NEXT_PUBLIC_*` leakage, kennitala (PII) reaching the client, `next.config.ts`
   headers/image hosts.
6. **Type discipline** — hand-rolled interfaces duplicating generated
   `api-types.ts` shapes, `any`/casts at the API boundary.
7. **Test coverage** — which of the above are protected by vitest, which aren't.

## Coverage of this pass

All seven passes ran. Read in full: `lib/api/{base,errors,server}.ts`,
`lib/auth-routing.ts`, `lib/uploadImage.ts`, `contexts/auth.tsx`,
`contexts/notifications.tsx`, `hooks/{useRequireAuth,useImageUpload}.ts`,
`components/{Dialog,CroppedImage,TagSelector,TagSidebarSelector}.tsx`,
`app/layout.tsx`, `next.config.ts`, all four `error.tsx`, all `*Dialog.tsx`,
the `app/old/**` entry points, the article-authoring hooks, `sanitize-schema.ts`,
`README.md`, `bundle-budgets.json`. Skimmed by grep: every `.tsx`/`.ts` under
`src/` for the security, duplication and type patterns listed above.

**Not covered** — if there is a next run, start here: `globals.css` beyond its
class inventory, `ImageCropper.tsx` (390 lines, 41 of them comments),
`components/InlineDiscussions.tsx` and the discussion components' state
handling, the `e2e/` suite, and whether the 28 vitest files leave meaningful
behaviour untested beyond `auth-routing.ts` (S1).

---

# Findings

Paths are relative to `src/web-ui/`.

## Security

### S1. Open redirect after login — `src/lib/auth-routing.ts:9`

`isSafeRedirect` rejects `//evil.com` but not `/\evil.com`. The WHATWG URL parser
treats `\` as `/` for http(s), so the backslash form resolves cross-origin:

```
$ node -e 'console.log(new URL("/\\evil.com", "https://naglasupan.is").href)'
https://evil.com/
```

`next` reaches it unvalidated from the query string (`app/login/page.tsx:18` →
`:33`/`:53`, same in `app/register/page.tsx:38`), so
`/login?next=/\evil.com` sends a **freshly authenticated** user to an attacker's
page. That is the shape phishing wants: the victim arrives having just typed
real credentials on the real domain.

Fix: resolve and compare origins rather than pattern-matching the string.

```ts
function isSafeRedirect(url: string): boolean {
  let dest: URL;
  try { dest = new URL(url, window.location.origin); } catch { return false; }
  if (dest.origin !== window.location.origin) return false;
  return !AUTH_PAGES.includes(dest.pathname) && dest.pathname !== "/";
}
```

Related, smaller: `AUTH_PAGES.includes(url)` is an exact string match, so
`next=/login?next=…` slips past the auth-page guard and can bounce a user
around the login screen.

**`auth-routing.ts` has no test file.** For a function whose whole job is
rejecting hostile input, that is the gap to close first — the fix above is
worth nothing without cases pinning `/\`, `//`, `https://`, `\/\/` and
`/login?x`.

### S2. CSP `script-src 'unsafe-inline' 'unsafe-eval'` — `next.config.ts:23`

Articles accept raw HTML from any `full_edit` contributor, and
`app/projects/[slug]/articles/sanitize-schema.ts` is the only thing standing
between that and script execution. The sanitizer is carefully built — but with
`'unsafe-inline'` in `script-src` there is no second line of defence: one
sanitizer bypass or one `rehype-sanitize` regression is immediate XSS against
every reader, with tokens sitting in `localStorage` (S3).

`'unsafe-eval'` in particular is a dev need; it doesn't have to ship to prod.
The file already branches on `isDev` (`next.config.ts:3`) for the CSP URLs, so
the mechanism is there. `'unsafe-inline'` for scripts is harder — Next's
bootstrap needs a nonce or hash strategy — but it's the change with the most
security per unit of effort in this codebase.

### S3. Tokens in `localStorage` — `src/lib/api/base.ts:47,56,65,73`

Access and refresh tokens live in `localStorage`, so any script running on the
page can read both — including the long-lived refresh token, which is the whole
session, not one hour of it. This is a deliberate architectural choice (server
components explicitly cannot authenticate as a result — see the comment at
`app/projects/[slug]/articles/ArticleAuthoringRoute.tsx:22`), so it is not a
"fix this" item. But it is what makes S2 expensive, and the two should be
weighed together rather than separately.

### S4. `src/app/old/**` is a live, unmaintained public route tree

Eight files, ~1,100 lines, **zero inbound references** from anywhere in `src/`
or `e2e/` — but App Router makes them real URLs. `/old/projects` and
`/old/projects/[id]` render and are crawlable today.

Consequences, in order:
- `app/old/projects/[id]/page.tsx:28` emits OpenGraph `url:
  https://naglasupan.is/projects/${id}` while being served from `/old/...` —
  two indexable URLs for the same project, one of them advertising the other's
  canonical.
- It is a frozen fork: `app/old/projects/[id]/discussions/DiscussionList.tsx`
  is the same file as the maintained
  `app/projects/[slug]/discussions/DiscussionList.tsx` minus the comment-anchor
  work (scroll-to, highlight, per-reply `id`). Every future discussion fix has
  to be made twice or silently isn't.

**Delete the directory.** This is the highest value-per-effort item in the
review — it removes ~1,100 lines, three of the duplications below, and a public
surface nobody is watching. Backend visibility rules still gate the data, so
it's cleanup, not an incident.

## Shared-component refactors

### R1. Lightbox — three copies

`app/projects/[slug]/ProjectDetailContent.tsx:253`,
`components/ImageUpload/ImageGallery.tsx:171`, and
`app/old/projects/[id]/ProjectDetailContent.tsx:237` are the same ~60-line
overlay: identical `fixed inset-0 z-50 bg-black/90 flex items-center
justify-center` root, identical close/prev/next buttons, identical
`pickVariant(…, "large") ?? url` fallback and `width || 1200 / height || 800`
defaults.

Extract `components/Lightbox.tsx` taking `images`, `index`, `onIndexChange`,
`onClose`. Two of the three copies disappear at once if S4 is done first.

Worth noting while doing it: none of the three traps focus or handles Escape —
`components/Dialog.tsx` gets both free from `<dialog>.showModal()`, so the
extraction is also the accessibility fix.

### R2. `PublishDialog` in `app/my-projects/[id]/` bypasses the shared `Dialog`

`app/my-projects/[id]/PublishDialog.tsx:20` hand-rolls a `<div
role="dialog" aria-modal="true">` overlay, while every other dialog in the app
(seven of them) uses `components/Dialog.tsx`. The hand-rolled one has no focus
trap, no Escape handling, no `aria-labelledby`, and no backdrop blur — it just
looks nearly right.

Two files also share the name `PublishDialog` with unrelated contents
(`app/projects/[slug]/articles/PublishDialog.tsx`), which makes both harder to
find. Rename the project one to `PublishBlockedDialog` — it reports missing
fields, it does not publish anything.

### R3. `TagSelector` / `TagSidebarSelector` — same data layer, two copies

`components/TagSelector.tsx` and `components/TagSidebarSelector.tsx` differ on
274 of ~470 lines, but the differences are all presentation. Byte-identical
between them: `loadTags` (`:27`/`:27`), the `groupedTags`/`isLoading`/`error`/
`suggestingFor`/`suggestName`/`isSuggesting` state block, `allTags`,
`getSelectedTags`, and the `handleSuggest` flow — the last of which is the one
that writes to the API.

Extract `hooks/useTagCatalog.ts` returning `{ groupedTags, isLoading, error,
allTags, getSelectedTags, suggestTag }`, leave the two components as pure
presentation. `TagSidebarSelector` already imports `SelectedTag` from
`TagSelector` (`:6`), so the coupling is acknowledged — it's just pointed at
the wrong thing.

### R4. `error.tsx` — four near-identical boundaries

`app/projects/error.tsx`, `app/projects/[slug]/error.tsx`,
`app/competitions/[id]/error.tsx`, `app/old/projects/[id]/error.tsx` differ only
in one noun ("projects" / "this project" / "this competition"), a `max-w-`, and
one stray `py-20` vs `py-8`. The button classes have already drifted apart
(`px-6 py-2.5 … font-medium shadow-sm` in one, `px-4 py-2` in the rest), which
is exactly how this fails: nobody notices until the pages sit side by side.

`components/ErrorBoundaryPage.tsx` taking `{ what: string; reset }` collapses
all four.

### R5. `HorizontalScroll` re-export shim

`app/projects/HorizontalScroll.tsx` is one line: `export { HorizontalScroll }
from "@/components/HorizontalScroll"`. Point the importers at
`@/components/HorizontalScroll` and delete the file — a shim with no
deprecation story is just a second name for one thing.

### R6. `UploadProgressItem` declared twice

`components/ImageUpload/UploadProgress.tsx:9` and
`app/my-projects/[id]/EditProjectContent.tsx:17` each declare their own. One
should import the other's, or both should come from `hooks/useImageUpload.ts`,
which already owns the near-identical `UploadProgress` shape (`:11`).

### R7. `ProjectDetail.tsx` — 14 `useState` in one component

`app/my-projects/[id]/ProjectDetail.tsx:43-60` holds fourteen independent state
slots (project, error, isLoading, viewMode, formData, formInitialized, isSaving,
isDeleting, showDeleteDialog, isPublishing, publishMissing, publishedProject,
competitionError, successMessage, images, selectedTags) across 539 lines.

The repo already solved this problem once, well: the article authoring route
splits into `useArticleLoad` / `useArticleForm` / `useArticleDraft` /
`useArticleMutations` / `useArticleImages`, each small and separately tested.
Apply that shape here — `useProjectLoad`, `useProjectForm`,
`useProjectMutations` — rather than inventing a new one.

`app/competitions/[id]/MyRanking.tsx` (536 lines) is second on the list, though
it is already internally decomposed (`RankingShell`, `Skeleton`,
`RankingActive`, `TabButton`, `StatusPill`) and has the best test file in the
repo, so it is far less urgent.

### R8. Hand-rolled types where generated ones exist

`components/TagFilterUnified.tsx:8,17,23` declares `TagData`, `CategoryData` and
`GroupedTagData` structurally mirroring `TagWithCategory` / `TagGrouped`, which
the same file already imports from `@/lib/api` (`:6`). These will drift from the
backend contract without a type error — the exact failure the generated-types
setup exists to prevent.

This is an isolated lapse, not a pattern: `lib/api/*.ts` aliases everything off
`components["schemas"][…]` and the rest of the app uses those aliases. Worth
fixing precisely because it's the only one.

## Documentation

### D1. `README.md` is unmodified `create-next-app` boilerplate

Every line is wrong for this project: it offers `yarn`/`pnpm`/`bun dev` (the
repo uses `npm ci` + `make`), points at `app/page.tsx` (it's `src/app/`),
describes a Geist font the app doesn't use (`app/layout.tsx:2` loads Inter and
JetBrains Mono), and closes with a Vercel deploy section for an app deployed via
Docker + k8s from the `naglasupan-hq` repo.

A reader following it gets a wrong answer at every step. Replace with ~15 lines:
what the app is, `npm ci`, the `make` targets, a link to root `CONTRIBUTING.md`
for the rest. Don't restate the commands that already live in `CLAUDE.md`.

### D2. Comments that argue the change rather than explain the code

Several files carry long comment blocks written as PR narration — they justify a
past decision to a reviewer instead of telling the next reader what the code
does. They are not wrong, they're in the wrong place, and they'll rot silently
because nothing tests a comment.

- `app/projects/[slug]/articles/ArticleAuthoringRoute.tsx:21-26` — "That is why
  authoring used to be unreachable on a project still in review" and "the same
  dead end this change exists to remove" (`:52-54`). Both describe a bug that no
  longer exists. The keeper is one sentence: *client-side fetch so the request
  carries the bearer token; a server component can't authenticate.*
- `app/projects/[slug]/articles/ArticleAuthoringRoute.tsx:35-42` — nine lines on
  why the editor import is warmed. The reason worth keeping is the bundle budget
  (`bundle-budgets.json` already encodes it: 40 kB eager / 400 kB lazy). Cut to
  two lines and cite the budget file.
- `components/CroppedImage.tsx:50-56` — "which is why articles predating
  cropping need no backfill" is migration history, not an explanation of the
  component.
- `app/projects/[slug]/articles/useLeaveGuard.ts:60-69` — ten lines on React's
  synthetic event system and the capture path. This one **earns its length**:
  it stops someone "tidying" the listener onto `document` and silently breaking
  the guard, and `use-leave-guard.test.tsx` backs it. Keep it.
- `app/projects/[slug]/articles/sanitize-schema.ts` — 50 comment lines in 130.
  Also earns it: every paragraph explains why a specific class is or isn't in an
  allowlist, and `markdown-parity.test.tsx` pins the behaviour. Keep.

The line to draw: comments explaining *why this code must stay this way* stay;
comments explaining *what a past change fixed* move to `docs/` or git history.

### D3. Banned phrase in a comment — `components/CroppedImage.tsx:83`

`// `maxWidth: "none"` is load-bearing.` — the expression is on the house
do-not-use list. The sentence after it already says the real thing ("a global
`img { max-width: 100% }` reset would cap the scaled image and silently shift
the crop"), so the fix is to delete the first four words.

### D4. `lang="en"` on Icelandic content — `app/layout.tsx:65`

`<html lang="en">` while the same file sets an Icelandic description
("Byggjum, deilum, vöxum saman", `:32`) and pages like `app/privacy/page.tsx`,
`app/about/why/page.tsx` and `app/notifications/page.tsx` are written in
Icelandic. Screen readers will pronounce them with an English voice; search
engines get the wrong language signal.

The UI is currently a mix (most chrome is English — "Loading...", "Delete
Project", "Publish article"), so this is worth a decision rather than a
one-character patch. Note the mismatch: `.claude/skills/nglspn-*/SKILL.md` both
state "user-facing strings are Icelandic", which the code contradicts almost
everywhere. One of the two should change.

## Smaller notes

- `app/verify-email/page.tsx:18`, `app/create/page.tsx:51`,
  `app/onboarding/page.tsx:34` each inline the same `<div
  className="text-muted-foreground text-sm">Loading...</div>`. `globals.css`
  already ships a `.skeleton` class (`:379`) nothing here uses.
- `useRequireAuth` (`hooks/useRequireAuth.ts:12`) redirects from inside an
  effect, so a protected page paints once before the redirect lands. Fine where
  callers gate on `isReady`; worth checking each caller does.
- `isReady: isAuthenticated || api.isAuthenticated()` (`:27`) is true whenever a
  token *string* exists, valid or not. Deliberate (it avoids a round trip before
  showing a skeleton) but easy to misread as "the session is good".

## Not problems

Checked and healthy — recording so a later pass doesn't re-tread:

- **Type discipline.** `lib/api/*.ts` aliases every shape off
  `components["schemas"][…]`. R8 is the only exception found.
- **Transient-vs-expired auth handling.** `lib/api/base.ts` distinguishes
  `refreshed`/`invalid`/`transient` and keeps tokens on transient failures;
  `lib/api/errors.ts` narrows by error *type*, not message text; `contexts/auth.tsx`
  defers to the client rather than second-guessing it. Tested in `base.test.ts`
  and `errors.test.ts`. This is the repo's known regression area and it is
  currently in good shape.
- **Image upload.** `lib/uploadImage.ts` is the single presign → PUT → complete
  path, with `useImageUpload` as the stateful wrapper. Dimension reading has a
  real fallback chain and returns `null` rather than throwing; the CSP/blob-URL
  interaction is handled and explained (`:110-118`).
- **`target="_blank"`.** All three occurrences carry `rel="noopener noreferrer"`.
- **No `dangerouslySetInnerHTML`** anywhere in `src/`.
- **Security headers.** HSTS, `nosniff`, `X-Frame-Options: DENY`,
  `frame-ancestors 'none'`, `Referrer-Policy`, `Permissions-Policy` all present
  and sensible. Only `script-src` (S2) is weak.

## Suggested order

1. Delete `app/old/**` (S4) — removes ~1,100 lines and three duplications.
2. Fix + test `isSafeRedirect` (S1).
3. Rewrite `web-ui/README.md` (D1); trim the D2/D3 comments while nearby.
4. Extract `Lightbox` (R1) and `ErrorBoundaryPage` (R4).
5. `useTagCatalog` (R3), then the `ProjectDetail` split (R7).
6. Decide the `lang` / language question (D4) — a product call, not a refactor.
7. Drop `'unsafe-eval'` from the prod CSP (S2); treat `'unsafe-inline'` as its
   own piece of work.
