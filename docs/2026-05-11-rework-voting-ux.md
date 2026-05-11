# Rework voting UX into a ranking view on the competition page

Issue: https://github.com/alexcouper/nglspn/issues/60
Branch: `rework-voting-ux`
Date: 2026-05-11

## Problem (from the issue)

- "My Reviews" is the only voting entry point and is hard to find — the name is misleading (it's actually voting/ranking).
- Drag-and-drop reordering breaks on touch devices.
- Logged-out visitors who land on a competition during voting have no obvious path to vote.

## Goal

Bring the ranking UX onto the competition page so that any visitor on `/competitions/[slug]` during a voting period can see and act on the ranking flow without going hunting through the nav menu, and so the mobile reordering is reliable.

## Non-goals

- Changing who is allowed to vote. The `CompetitionReviewer` model remains the source of truth for voting eligibility — admins still pre-assign reviewers (currently via the "Add all reviewers" admin button). Opening voting to all logged-in users is a separate product call and would need backend work; the issue does not require it.
- Server-rendering the ranking. The ranking is per-user, mutates frequently, and needs auth headers, so it stays a client component fetched after hydration. The competition page itself is still SSR'd.
- Migrating away from `@dnd-kit`. We keep the existing pointer-based drag, just make it work on touch and add a fallback path.

## Scope decisions

### 1. Embed the ranking on the competition page, don't link out

The original UX put the ranking on `/my-reviews/[competitionId]`. Instead of linking to that from the competition page, we render the ranking *in place*. One page = one canonical "this competition" surface. This kills the "users don't know it exists" failure mode and gives logged-out visitors a natural place to be prompted to log in.

### 2. Eligibility surfaces are layered, not gated

The same `<MyRanking>` block is rendered for every visitor when `competition.status === "voting"`, but its content branches:

| Visitor state                                | What we show                                                              |
| -------------------------------------------- | ------------------------------------------------------------------------- |
| Logged out                                   | Login CTA (`/login?next=/competitions/<id>`) + register link              |
| Logged in, **not** an assigned reviewer      | Friendly explainer that voting is invite-only this round                  |
| Logged in, assigned reviewer, in progress    | The ranking list with drag handles + up/down buttons + "Submit" button    |
| Logged in, assigned reviewer, completed      | "You've submitted" confirmation, projects shown in the order they ranked  |
| Logged in, assigned reviewer, ended by admin | Read-only view: "Voting period ended"                                     |

The "not assigned" state is detected by the existing `GET /api/my/reviews/competitions/{id}` returning 404. To distinguish that 404 cleanly from network errors, we extend `ApiRequestError` with `status` (today it only carries `body`).

### 3. Mobile reordering: belt-and-braces

The current drag uses only `PointerSensor`. On iOS Safari that captures touch events but the drag handle is a tiny `Bars3Icon`, and once you grab it the page wants to scroll. Two layers of fix:

1. **TouchSensor with a press delay** in addition to PointerSensor. A 200ms hold disambiguates "I'm trying to scroll" from "I'm trying to drag", which is the standard `@dnd-kit` recipe for touch.
2. **Up / Down buttons** on each ranking row. These are the reliable fallback — they require zero gesture interpretation, and on small screens they're often faster than dragging anyway. Buttons are disabled at the ends (top can't go up, bottom can't go down) and are visible on every screen size, not just mobile, because keyboard users benefit too.

### 4. Visible submission state

Both the ranking block header and the page-level voting banner reflect submission state:

- "Save in progress" / "Saved" microcopy under the list (existing behavior, kept).
- A pill on the ranking header showing **In progress** / **Submitted** / **Voting ended**.
- Once submitted, the ranking is read-only and the "Submit" button is replaced with a small "Reopen ranking" link (which calls `updateStatus("in_progress")`). The original `/my-reviews` flow also let you reopen — we keep that affordance.

### 5. Deprecate `/my-reviews`, redirect rather than delete

The acceptance criteria say "Deprecate My Reviews section". Hard-deleting the routes would 404 anyone with a bookmark. Instead:

- Remove the **"My Reviews" links from `Navigation.tsx`** (desktop + mobile).
- Replace `/my-reviews/page.tsx` with a `redirect()` to `/competitions`.
- Replace `/my-reviews/[competitionId]/page.tsx` with a `redirect()` to `/competitions/[id]`.
- Leave `/my-reviews/[competitionId]/[projectId]` for now — the project detail link target moves to `/projects/[slug]` from the new ranking, so the old per-project review page is unreferenced; we redirect that to `/projects/[id]` for safety.
- Delete the supporting client-only files that nothing else uses (`CompetitionsList`, `CompetitionProjects`, `BreadcrumbContext`, `Breadcrumbs`, `FinishReviewDialog`, `layout.tsx`). The new in-place component is built fresh — it shares the *backend* API but not the wrapper UI.

Reasoning: the only reason to keep the old layout/breadcrumb scaffolding alive is if other code imported from it. A grep confirms nothing outside `/my-reviews` does, so leaving it in place is dead-code drag.

### 6. No backend changes

Everything is satisfied by the existing endpoints:

- `GET /api/competitions/{id}` (already used by the page) tells us status and project list.
- `GET /api/my/reviews/competitions/{id}` returns assignment + ranking (or 404 if not assigned).
- `PUT /api/my/reviews/competitions/{id}/rankings` saves order.
- `PUT /api/my/reviews/competitions/{id}/status` finishes/reopens.

The only "infrastructure" tweak is adding `status` to the client-side `ApiRequestError` so the 404 can be detected without parsing the message.

## Files touched

### New

- `src/web-ui/src/app/competitions/[id]/MyRanking.tsx` — the embedded ranking block. Owns its own data fetching and state.
- `src/web-ui/src/app/competitions/[id]/RankingList.tsx` — the dnd-kit list + up/down buttons + project rows. Pure presentation; takes ordered projects + callbacks.
- `src/web-ui/src/app/competitions/[id]/SubmitRankingDialog.tsx` — confirmation modal (replaces `FinishReviewDialog`, same shape).

### Modified

- `src/web-ui/src/app/competitions/[id]/CompetitionReveal.tsx` — render `<MyRanking competitionId={...} status={...} />` between the voting banner and the "All Projects" grid.
- `src/web-ui/src/app/my-reviews/page.tsx` — replace with `redirect("/competitions")`.
- `src/web-ui/src/app/my-reviews/[competitionId]/page.tsx` — replace with `redirect(\`/competitions/${competitionId}\`)`.
- `src/web-ui/src/app/my-reviews/[competitionId]/[projectId]/page.tsx` — replace with `redirect(\`/projects/${projectId}\`)`.
- `src/web-ui/src/components/Navigation.tsx` — remove "My Reviews" entry from desktop and mobile menus.
- `src/web-ui/src/lib/api/base.ts` — `ApiRequestError` gains `public status: number`.

### Deleted

- `src/web-ui/src/app/my-reviews/CompetitionsList.tsx`
- `src/web-ui/src/app/my-reviews/Breadcrumbs.tsx`
- `src/web-ui/src/app/my-reviews/BreadcrumbContext.tsx`
- `src/web-ui/src/app/my-reviews/layout.tsx`
- `src/web-ui/src/app/my-reviews/[competitionId]/CompetitionProjects.tsx`
- `src/web-ui/src/app/my-reviews/[competitionId]/FinishReviewDialog.tsx`

## Acceptance criteria mapping

| Acceptance criterion                                                       | Where it lands                                                                                                          |
| -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| One-click access to ranking view from competition page                     | Ranking block is inline on the competition page during voting; no link to follow                                        |
| Mobile-friendly reordering functionality                                   | TouchSensor with delay + explicit Up/Down buttons; buttons work without any drag                                        |
| Clear voting CTA with login flow for logged-out visitors                   | Logged-out branch of `<MyRanking>` shows a login CTA pointing back at the same competition page                         |
| Visible submission state indicator                                         | Header pill ("In progress" / "Submitted" / "Voting ended") + microcopy + button state under the list                    |
| Deprecate "My Reviews" section                                             | Nav links removed; `/my-reviews/*` routes redirect to the new home; old client UI deleted                               |

## Reviewer notes

- **Why the ranking isn't its own route under `/competitions/[id]/vote`**: an extra route brings back the same "where is voting?" failure mode that the issue is solving. The whole point is to make voting feel like part of looking at the competition. If you want it as a separate URL later (e.g., for sharing a deep link), it'd be one extra route reusing `<MyRanking>`.
- **Why we don't auto-assign on visit**: would silently change the meaning of `CompetitionReviewer` (currently "people the admin invited") and would break the admin's "X people are assigned" mental model. Out of scope.
- **Why up/down buttons live alongside drag, not instead of it**: drag is faster on desktop and `@dnd-kit` is already wired up — removing it would be a regression for the existing happy path.
- **Mobile testing note**: I ran `npm run lint` and `npm run build` locally, but full mobile interaction verification needs a real device (this branch is being prepared while you're offline). The buttons path is gesture-free and should work everywhere; the drag path is the one to spot-check on iOS Safari.
