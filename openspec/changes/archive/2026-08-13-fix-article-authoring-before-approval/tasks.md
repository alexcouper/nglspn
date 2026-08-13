# Tasks: fix article authoring before project approval

## 1. Pin the backend behaviour

- [x] 1.1 In `src/django-backend/api/routers/test_articles.py`, add tests that a `full_edit` contributor can `POST /api/projects/{id}/articles` on a project with `status = DRAFT` and with `status = PENDING`, parametrised over the two statuses.
- [x] 1.2 Extend the same parametrisation to `PATCH`, `POST .../publish` and `DELETE` on an article belonging to a non-approved project, asserting each succeeds as it does on an approved one.
- [x] 1.3 Run `make test` in `src/django-backend/` and confirm the new tests pass without touching production code — if any fails, the premise in `design.md` is wrong and the change needs rethinking before continuing.

## 2. Extract the loading skeleton

- [x] 2.1 Pull the skeleton markup at `src/web-ui/src/app/projects/[slug]/articles/ArticleAuthoringPage.tsx:60-70` into a component (`ArticleAuthoringSkeleton`) in the same directory.
- [x] 2.2 Render it from `ArticleAuthoringPage` in place of the inlined markup, so the extraction is behaviour-neutral on its own.

## 3. Add the client route wrapper

- [x] 3.1 Create `src/web-ui/src/app/projects/[slug]/articles/ArticleAuthoringRoute.tsx` as a client component taking `{ projectRef: string; articleId?: string }`.
- [x] 3.2 Call `useRequireAuth()` in it and hold the project fetch until `isReady`; render `ArticleAuthoringSkeleton` while auth is settling.
- [x] 3.3 Fetch the project with `api.projects.get(projectRef)` once ready, rendering `ArticleAuthoringSkeleton` while in flight.
- [x] 3.4 On failure, render an in-page message (heading plus `describeApiError` text, matching the existing failure blocks in `ArticleAuthoringPage`) with a link back to `/my-projects`.
- [x] 3.5 On success, render `<ArticleAuthoringPage project={project} articleId={articleId} />` — prop signature unchanged.
- [x] 3.6 Guard the fetch against unmount so a late response cannot set state on a torn-down component, following the `cancelled` pattern in `useArticleLoad.ts:43`.

## 4. Reduce the route pages to server shells

- [x] 4.1 Rewrite `src/web-ui/src/app/projects/[slug]/articles/new/page.tsx` to render `<ArticleAuthoringRoute projectRef={slug} />` with no `getProjectOr404` call.
- [x] 4.2 Rewrite `src/web-ui/src/app/projects/[slug]/articles/edit/[articleId]/page.tsx` to render `<ArticleAuthoringRoute projectRef={slug} articleId={articleId} />`, likewise with no server fetch.
- [x] 4.3 Remove the now-unused `useRequireAuth()` call and its `isReady`/`authLoading` branches from `ArticleAuthoringPage`, keeping `useAuth().user` for the `canEdit` check.
- [x] 4.4 Check whether `getProjectOr404` still has callers in `src/web-ui/src/lib/api/server.ts`; leave it if the article render page and project page still use it, remove it if not.

## 5. Frontend tests

- [x] 5.1 Add `src/web-ui/src/app/projects/[slug]/articles/article-authoring-route.test.tsx`, following the mocking style of `use-article-draft.test.tsx`.
- [x] 5.2 Test: with auth ready and `api.projects.get` resolving an unapproved project, the authoring UI renders.
- [x] 5.3 Test: with `api.projects.get` rejecting with a 404, the in-page error and the `/my-projects` link render, and the authoring UI does not.
- [x] 5.4 Test: while `useRequireAuth` reports not-ready, `api.projects.get` is never called.

## 6. Verify

- [x] 6.1 Run `make lint` and `make test` in `src/web-ui/`.
- [x] 6.2 Run `make build-app` and `make extra-tests` in `src/web-ui/` — the routes lose their server fetch, which moves them between static and dynamic rendering, so confirm the per-route bundle budgets still hold.
- [x] 6.3 Run `make lint`, `make extra-tests` and `make test` in `src/django-backend/`; `extra-tests` should pass untouched since no endpoint changed.
- [x] 6.4 Manual pass: with the backend and web-ui running against a seeded database, open a project with `status = DRAFT` at `/my-projects/<id>`, click **Articles → New article**, confirm the editor opens, save a draft and reopen it from the tab.
- [x] 6.5 Manual pass: log out and hit `/projects/<identifier>/articles/new` directly; confirm a redirect to login rather than a 404.
