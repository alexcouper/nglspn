# Fix article authoring before project approval

## Why

A contributor with `full_edit` on a project that is not yet `APPROVED` clicks
**New article** and gets a Next.js 404. The Articles tab in `/my-projects/<id>`
lists fine — it fetches client-side with the bearer token — so the failure only
shows up on the click, with no explanation.

Nothing in the backend forbids this. `create_article`, `patch_article` and
`publish_article` all gate on `require_full_edit` (`api/routers/_helpers.py:35`),
which checks project membership and never `status`. The 404 comes from the
frontend: `articles/new/page.tsx:9` and `articles/edit/[articleId]/page.tsx:9`
are server components calling `getProjectOr404(slug)`, and `serverFetch`
(`lib/api/server.ts:30`) sends no credentials — the bearer token lives in
`localStorage`, which no server component can read. The backend therefore sees
an anonymous caller, and `get_project` (`api/routers/projects.py:183`) 404s
anything not `APPROVED`.

The result is that a team cannot write launch content while their project is in
review — the one window where they most want to.

## What Changes

- The authoring routes fetch the project **client-side**, with credentials, so
  the page opens for any `full_edit` contributor regardless of project status.
- A new client wrapper, `articles/ArticleAuthoringRoute.tsx`, owns
  `useRequireAuth()` and the project fetch. `articles/new/page.tsx` and
  `articles/edit/[articleId]/page.tsx` shrink to server shells that pass route
  params through.
- `ArticleAuthoringPage` keeps its `project: Project` prop and drops its own
  `useRequireAuth()` call — the wrapper now gates on it. Every hook below it
  (`useArticleDraft` and its four sub-hooks) is untouched.
- Backend tests pin the permissive behaviour that `require_full_edit` already
  has, so a future status check cannot be added to article endpoints by
  accident.

Not breaking: no API, schema or route changes. `backend-openapi.json` is
unaffected.

### Explicitly out of scope

- **`/projects/<slug>` still 404s for its own contributors while unapproved.**
  Same root cause, but it is the public project page rather than an authoring
  surface, and an invisible project having an invisible page is defensible.
- **A published article on an unapproved project still 404s on its public URL**,
  for its author too. Consistent with the project being invisible, and it
  resolves itself on approval. The general "author cannot see their own
  unpublished content" gap is tracked as item 7 in `FOLLOW_UPS.md`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `articles`: the **Authoring endpoint and entry point** requirement gains the
  guarantee that the authoring page is reachable for a `full_edit` contributor
  on a project in any status, plus the auth-redirect and project-not-found
  behaviours the client-side fetch now owns.

## Impact

**Frontend** (`src/web-ui/`):

- `src/app/projects/[slug]/articles/ArticleAuthoringRoute.tsx` — new.
- `src/app/projects/[slug]/articles/new/page.tsx` — server shell only.
- `src/app/projects/[slug]/articles/edit/[articleId]/page.tsx` — server shell only.
- `src/app/projects/[slug]/articles/ArticleAuthoringPage.tsx` — drops
  `useRequireAuth`; its loading skeleton is extracted so the wrapper renders the
  same one.
- `api.projects.get()` (`src/lib/api/projects.ts:44`) gains a second caller. No
  change to the client itself.

**Backend** (`src/django-backend/`): tests only. No router, service, schema or
model changes, and therefore no migration and no OpenAPI regeneration.
