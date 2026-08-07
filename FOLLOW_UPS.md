# Follow-ups — following page

Small UX gaps found on `/profile/following`. Neither blocks anything; both are
frontend-only.

## 1. No way to unfollow a single channel from the following page

`src/web-ui/src/app/profile/following/page.tsx:168`

Expanding a row lists the project's channels, but each one renders as a static
`Followed` / `Not followed` badge. The only mutation on the page is the
whole-project `Unfollow` button (`page.tsx:150`), so narrowing a subscription —
the common case once you follow more than a handful of projects — means visiting
each project page and using the follow popover there. The page header says as
much (`page.tsx:60`: "Manage per-channel subscriptions from each project's
page"), so this is a deliberate limitation rather than an oversight, but it makes
the one screen that shows every subscription the one screen where you can't
adjust them.

The plumbing already exists: `api.follows.followChannel` /
`unfollowChannel` (`src/web-ui/src/lib/api/follows.ts:38,48`), used by
`src/web-ui/src/components/FollowPopover.tsx:69`. The work is swapping the badge
for a toggle and reusing the popover's optimistic-update handling — including its
rollback on failure, since the list here is loaded once and never refetched.

## 2. The empty-state link points at `/discover`, which 404s

`src/web-ui/src/app/profile/following/page.tsx:82`

```tsx
<Link href="/discover" className="text-accent hover:underline">
  Discover projects
</Link>
```

There is no `/discover` route and no redirect or rewrite for it in
`src/web-ui/next.config.ts`. Discover lives at `/projects` — that's what the
"Discover" tab links to (`src/web-ui/src/app/projects/CategoryTabs.tsx:17`).

So a user with no follows sees the empty state and the single call to action on
it is dead. Fix is `href="/projects"`. This is the only `/discover` reference in
`src/web-ui/src`.
