# Design: fix article authoring before project approval

## Context

See [`proposal.md`](proposal.md) for the motivation. In short: the authoring
routes are server components that resolve the project anonymously, and
`get_project` (`api/routers/projects.py:183`) 404s any project that is not
`APPROVED` for an anonymous caller.

The constraint behind all of it: auth in this app is a bearer token in
`localStorage`. No server component can read it, so **every** server-rendered
page here is effectively anonymous. `FOLLOW_UPS.md` item 7 records the same
constraint biting draft article previews. This change does not lift the
constraint; it moves one fetch out from under it.

What already works, and is worth stating so the diff stays small:

- `MyProjectArticles` lists articles client-side with the token, so the Articles
  tab in `/my-projects/<id>` is healthy on a draft project today.
- The whole authoring surface below the route — `ArticleAuthoringPage` and the
  five hooks under `useArticleDraft` — is `"use client"` and already
  authenticates every call it makes.
- `GET /api/projects/{identifier}` accepts a slug **or** a UUID
  (`services/project/django_impl/query.py:150`) and, given a token, returns an
  unapproved project to anyone with edit rights (`api/routers/projects.py:179`
  onwards). It needs no backend change.

So the only broken hop is the one server fetch.

## Goals / Non-Goals

**Goals:**

- A `full_edit` contributor can open the authoring page on a project in any
  status.
- The fix is confined to the route layer. No hook below `ArticleAuthoringPage`
  changes.
- The permissive backend behaviour stops being accidental and gets test cover.

**Non-Goals:**

- Fixing `/projects/<slug>` for contributors of unapproved projects. Same cause,
  but that is the public project page; an invisible project having an invisible
  page is coherent, and the author reaches their content through
  `/my-projects/<id>` anyway.
- Making a published article on an unapproved project readable at its public
  URL. It stays 404 until the project is approved.
- Any general "authenticated server rendering" mechanism. One route pair moves
  to the client; that is the whole change.

## Decisions

### A client wrapper component, not a nullable project prop

`ArticleAuthoringPage` takes `project: Project` and passes it straight into
`useArticleDraft`, which derives `projectRef` and threads it through five hooks.
Making the project loadable in place would mean `project: Project | null`
propagating into all of them, each learning a no-op state — hooks cannot be
called conditionally.

Instead a new `articles/ArticleAuthoringRoute.tsx` (client) loads the project
and renders `ArticleAuthoringPage` only once it has one. `ArticleAuthoringPage`
keeps a non-null `project` and every hook below it is untouched.

*Alternative considered:* pass the project as a promise and `use()` it inside
`ArticleAuthoringPage` with a Suspense boundary in the page. That keeps the
server component but not the credentials — the fetch would still be anonymous.
It solves a different problem.

### The wrapper owns `useRequireAuth`, and gates the fetch on it

Order matters. Fetching before auth settles would show an unauthenticated
visitor a "couldn't open this project" message on the way to a login redirect —
the 404 problem in a new costume. The wrapper calls `useRequireAuth()` first and
only requests the project once `isReady`.

`ArticleAuthoringPage` therefore drops its own `useRequireAuth()` call. It keeps
`useAuth().user`, which its `canEdit` check needs.

### `api.projects.get`, not `api.myProjects.get`

`api.myProjects.get` (`lib/api/my-projects.ts:29`) takes a UUID only, but the
`[slug]` route param is a slug or a UUID depending on whether the project has
one — `MyProjectArticles` builds the link as `project.slug ?? project.id`.
`api.projects.get` (`lib/api/projects.ts:44`) accepts either and is the same
endpoint the server component was already calling, so the only thing that
changes about the request is that it now carries a token.

### Failure renders in-page, not `notFound()`

`notFound()` works in client components, so this is a choice rather than a
constraint. An authenticated user reaching this route came from
`/my-projects/<id>`; a 404 with no route back is a dead end, and the page
already has the vocabulary for in-page failure — it renders "Not allowed" for a
lost `full_edit` and "Couldn't open this article" for a dead draft. Project
resolution failure joins them, with a link back to `/my-projects`.

### The loading skeleton is extracted, not duplicated

`ArticleAuthoringPage` renders a skeleton while `draft.isLoading`
(`ArticleAuthoringPage.tsx:60`). The wrapper needs one for the project fetch
that precedes it. Extracting the existing markup into a small component keeps
the two phases visually identical, so the load reads as one wait rather than two
with a layout shift between them.

### Backend: tests only

`require_full_edit` checking membership and not status is correct, but it is
correct only implicitly — nothing fails if someone adds a status guard. Tests
across `DRAFT` and `PENDING` pin it. No production code changes, so no
migration, and `backend-openapi.json` is untouched.

### Spec correction carried along

The `articles` spec names the edit route `/articles/<id>/edit`; the route on
disk is `/articles/edit/<id>`. The delta spec corrects it, since MODIFIED
requires restating the block anyway and this change is what touches that route.

## Risks / Trade-offs

- **The authoring page now renders a client-side loading state where it
  previously arrived fully resolved.** → The extracted skeleton makes it the
  same skeleton the article load already shows, so the perceived change is a
  slightly longer wait, not a new visual step.
- **`useRequireAuth` moving up could change behaviour for the onboarding
  redirect** (it also pushes to `/onboarding` for users with pending steps). →
  It is the same hook with the same inputs, one component higher, and it now
  runs strictly *before* rather than *alongside* the project fetch. The redirect
  is unchanged; only the fetch is newly ordered after it.
- **An author can now publish an article on a project that is still in review,
  and the article's public URL 404s.** → Accepted. The project's own page 404s
  identically, and approval resolves both. The confusing case — an author unable
  to preview their own unpublished work — is pre-existing and tracked as item 7
  in `FOLLOW_UPS.md`.
- **Playwright cover is impractical here.** Login is rate-limited to 5 requests
  per minute per IP (`api/rate_limit.py`) and the scenario needs a seeded draft
  project. → Covered by a vitest component test plus a manual pass; no e2e spec.

## Migration Plan

None. No schema, no data, no API contract. Deploying is shipping the frontend
build; rolling back is reverting it.

## Open Questions

None outstanding. The two that were open at design time are settled: the
sibling `/projects/<slug>` 404 stays as-is, and project-resolution failure
renders in-page rather than calling `notFound()`.
