# Handoff — applying the review feedback

For a fresh session picking up this work. Read this, then `00-INDEX.md`, then
only the documents for the items being worked on.

## What this is

A review of the article-authoring branch produced `review/00-SUMMARY.md`. Alex
annotated each finding with a comment beginning `Alex:`. Those comments were
answered in 21 documents under `review/feedback/`, each containing either an
answer to his question or a proposed patch.

**Nothing has been applied.** Every document is a proposal. No source file,
test, workflow, Makefile, `.gitignore` or `CLAUDE.md` has been touched by this
work — the only additions are the review documents themselves.

**Alex has a specific set he wants to work on, and has not yet named it.** Ask
which items at the start of the session rather than assuming; the index is
ordered by finding, not by priority.

## Repository state

| | |
|---|---|
| Repo | `/Users/alex/Work/codalens/nglspn/nglspn-hq` |
| Branch base (`main`) | `d2463b33` "Democratic ranking (#74)" |
| Branch tip reviewed | `7a20fb38` (jj change `swzk`) |
| Working-copy change | jj `svls` — "Review feedback: responses and fix proposals per finding" |
| Parent | jj `xyly` `2aa5f1ec` — "Add additional review (temp - will be removed)" |

Full branch diff: `git diff d2463b33a7063bd4dae20b8add728aaf5046b8b2...7a20fb38`

`review/` is tracked. Document `18` recommends it does **not** merge — fold
durable output into `openspec/changes/*/feedback.md` and delete the directory
once the proposals are actioned. That deletion must come last.

## Version control

**Use jj, not git.** This is a colocated repo and git HEAD lags jj's working
copy — `git status` reports phantom modifications for changes jj considers
committed. This is not cosmetic: document `09` deliberately avoids
`git diff --exit-code` for the OpenAPI drift check for exactly this reason, and
document `17` gives jj-native untracking rather than `git rm --cached`.

Standard flow, per `~/.claude/CLAUDE.md`:

```bash
jj status                      # check if the working copy is empty
jj describe -m "<what>"        # if empty, describe it
jj new -m "<what>"             # if not, start a fresh change
```

Do not add `Co-Authored-By` or "Generated with Claude Code" trailers.

## Verification baseline

Measured on the branch as reviewed. Use these to tell a regression from a
pre-existing condition.

```
src/django-backend:  make lint          pass (353 files)
                     make test          1111 passed, ~4m40s
                     makemigrations --check --dry-run   No changes detected
                     make extract-openapi → byte-identical to committed spec

src/web-ui:          npm run lint       pass (eslint + tsc --noEmit)
                     npm run test       153 passed, 11 files
```

`make extract-openapi` **writes** `src/web-ui/backend-openapi.json` in place —
regenerate to a temp path or restore afterwards.

CI (`.github/workflows/ci.yml`) currently runs backend lint+test and web-ui
lint+build only. It does **not** run vitest or Playwright — that is what
documents `08`/`09` change. So a green CI today does not mean the frontend tests
pass.

Note: `make e2e` in `src/web-ui/Makefile` is broken independently of this branch
— it sets `TEST_APP_URL` from `scripts/find-free-port.sh`, which by definition
returns a port with nothing listening on it. Don't use it as a smoke test.

## House rules that bite here

- **OpenAPI contract.** Any change to `api/routers/*.py` or `api/schemas/*.py`
  that alters a request/response shape, status code or endpoint requires
  `make extract-openapi` and committing `src/web-ui/backend-openapi.json` in the
  same change. `src/web-ui/src/lib/api-types.ts` is gitignored — its absence is
  correct.
- **Migrations.** Any `apps/*/models.py` change needs a matching migration.
- **Layering.** Writes via `HANDLERS.<domain>`, reads via `REPO.<domain>`, both
  `from services import HANDLERS, REPO`. Routers orchestrate; no raw ORM in a
  router. Auth via the shared `_helpers` (`require_full_edit`,
  `resolve_visible_project_or_404`, `get_optional_user`).
- **Tests.** pytest + factory-boy on the backend, vitest on the frontend.
  Descriptive test names over docstrings; helper asserts and factories.

## Corrections carried forward

These were established against the code during this round. Re-deriving them
costs time; contradicting them will produce wrong work.

1. **`transaction.on_commit` is wrong for task enqueue.** `django-tasks` and
   `django-tasks-db` are both 0.12.0 and neither defines `ENQUEUE_ON_COMMIT`.
   The enqueue is an INSERT in the caller's transaction, so it belongs *inside*
   `transaction.atomic()`; `on_commit` opens a lost-enqueue window. (Doc `03`.)
2. **The web-ui is English, not Icelandic.** The `nglspn-code-review` skill says
   otherwise and is wrong. The only Icelandic in `src/web-ui/src` is the wordmark
   and the `layout.tsx:32-33` tagline; there is no i18n infrastructure. Match the
   surrounding English. (Doc `15`.)
3. **`ArticleUpdate` is all-optional and `patch_article` uses `exclude_unset`**,
   so `api.articles.update(ref, id, {})` is expressible today — no schema change
   needed for doc `06`.
4. **The guard test in `test_articles.py:902` is a substring check.** The
   router's real ORM access is `get_object_or_404(ProjectImage, …)` at
   `articles.py:292`, which contains no `.objects`, so banning
   `"ProjectImage.objects"` is vacuous. Ban `get_object_or_404`. (Doc `21`.)
5. **`CLAUDE.md` and `CONTRIBUTING.md` are both stale.** `make ci`,
   `scripts/ci/` and `infra/prod/app/` do not exist; Terraform lives in a
   separate `naglasupan-hq` repo; `infra/` here holds only `grafana/`. Don't
   trust either file's paths or commands. (Doc `19`.)

## Counts corrected from the original review

If a document and `00-SUMMARY.md` disagree on a number, the document is right.

- I1 is **three** prefetch sites (`handler.py:328`, `:363`, `:377`) — the
  summary says two, missing the discussion bell.
- `REPO.images` touches **eight** call sites, not four, including
  `my_review.py:24,216` and `competition.py:12,71` importing `django_impl`
  directly.
- Prism registers **333** grammars, not 297.
- MDXEditor adds **186** packages, not 242.

## The one blocker found while answering

Not in `00-SUMMARY.md` — it surfaced in doc `04`.

`useArticleDraft.ts:162` sweeps drafts on unmount and `isUntouched` (`:43`)
checks neither `article.state` nor whether the article arrived with content. So
clearing the title and body of a **published, image-less** article and
navigating away calls `api.articles.delete` — the published article is deleted
from the server, with no timing window. Only one `<Link>` on the page consults
`isDirty()` (`ArticleAuthoringPage.tsx:154`); nav-bar links and browser Back
bypass it, and that prompt mentions unsaved changes, never deletion.

The same fix closes the narrower mid-upload race that doc `04` was asked about.
If any subset of this work ships, this should be in it.

## Sequencing constraints

```
independent:    17
one ci.yml edit: 08 + 09   →  then 19 (documents the resulting pipeline)
land together:  11 + 21    (the guard assertion fails until the refactor lands)
                11 + 01    (01 happened because the right spelling lived elsewhere)
fix before refactor: 04, 05  →  then 10 (decomposition fixes neither bug)
last:           18's `review/` cleanup, after every actioned proposal
```

## Decisions Alex has already made

Recorded so they are not reopened:

- **B1** (digest cron rename) — "this is fine. Already sorted."
- **B2** (column drops, no drain window) — "maintenance window scheduled."
- **I8** (`users/0018` cohort) — "Notification frequency was only about
  discussions before. We're good here."

## Decisions still open

Listed with the recommendation from the relevant document:

1. **02** — tombstone table (recommended) vs deleting through
   `HANDLERS.images.delete_image`. The tombstone also drains `FOLLOW_UPS` item 5.
2. **06** — ship the empty-`PATCH` fix now, send draft revisions to follow-ups.
3. **07** — whether re-following re-enrols channels on an emptied Follow
   (recommendation: yes, only when there is nothing to preserve).
4. **13** — grammar subset now (recommended) vs server-render later.
5. **18** — whether `review/` merges at all (recommendation: no).
