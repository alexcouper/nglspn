<!--
  Keep it proportional: a one-line fix needs a sentence or two, not every
  heading below. A multi-step feature deserves the full shape. Delete sections
  that don't apply.
-->

## Summary

<!-- What does this change do, in a sentence or two? If it's part of a larger
     plan, say where it fits (e.g. "Phase 3 of the Articles design", link the
     OpenSpec change or design doc). -->

## What's in this PR

<!-- The notable changes, grouped backend / frontend / infra if that helps.
     Enough that a reviewer knows what to look at — not a restatement of the diff. -->

## Out of scope

<!-- Anything deliberately deferred, so reviewers don't flag it as missing.
     Delete if nothing applies. -->

## Test plan

- [ ] Backend: `cd src/django-backend && make lint && make test`
- [ ] Frontend: `cd src/web-ui && npm run lint && npm test`
- [ ] OpenAPI regenerated if the API changed (`make extract-openapi`, `backend-openapi.json` committed)
- [ ] Migration added if a model changed
- [ ] OpenSpec validated if this is part of a change (`openspec validate <name>`)
- [ ] Manual / Playwright check (describe, or note why deferred)

## Verification

<!-- The result of the above: e.g. "851 tests pass. Lint clean.
     openspec validate clean." Reviewers trust this line — only check what you ran. -->

Closes #
