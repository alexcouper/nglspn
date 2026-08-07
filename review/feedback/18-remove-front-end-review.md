# 18. Delete `FRONT_END_REVIEW.md`, keep `FOLLOW_UPS.md`

**Finding:** Minor — three scratch review docs are committed at the repo root.
**Alex:** Remove FRONT_END_REVIEW but let's keep follow ups, it'll ironically be deleted in a follow up
**Type:** fix proposal
**Effort:** S, one deletion. The only work is deciding what happens to `review/`.

## What is actually happening

Root-level state right now:

| File | Tracked | Status |
|---|---|---|
| `REVIEW.md` | no | already deleted, in jj change `xyly 2aa5` |
| `FRONT_END_REVIEW.md` | yes | 14,047 bytes, added in `4420ffd1` — to delete |
| `FOLLOW_UPS.md` | yes | 8,414 bytes — keep, per your call |
| `QUESTIONS.md` | yes | 9,447 bytes, from a prior round — untouched, out of scope |
| `docs.md` | yes | the documentation map, genuinely product |
| `review/` | yes | 6 files, added in `2aa5f1ec` — see below |

### Who references `FRONT_END_REVIEW.md`

Full sweep, excluding `.git`, `.jj` and `node_modules`:

| Location | Line | Nature |
|---|---|---|
| `review/00-SUMMARY.md` | 4 | prose — "reviewed without reference to `REVIEW.md` / `FRONT_END_REVIEW.md` / `FOLLOW_UPS.md`" |
| `review/00-SUMMARY.md` | 283, 287 | the finding and your comment on it |
| `review/05-crosscutting-review.md` | 279, 539 | §4.2 and Minor 7 |
| `REVIEW.md` @ `7a20fb38` | 172 | "(`FRONT_END_REVIEW.md`, landed in `678dc07e`)" — moot, `REVIEW.md` is already gone |
| commit messages `4420ffd1`, `678dc07e` | — | immutable, will dangle by design |

**Nothing in `openspec/`, `docs/`, `CONTRIBUTING.md`, `docs.md`, `FOLLOW_UPS.md`, or any source file references it.** The only live references are inside this review directory, which is itself temporary (below). So the deletion leaves no dangling reference anywhere that will survive the merge — nothing to fix, nothing to knowingly leave broken.

For contrast, `FOLLOW_UPS.md` **is** referenced from source:

```
src/web-ui/src/app/projects/[slug]/articles/[articleSlug]/page.tsx:67
  // FOLLOW_UPS.md item 7.
```

and from `FOLLOW_UPS.md:107` back at the now-deleted `REVIEW.md` ("Raised as finding 9 of `REVIEW.md`"). That second one is already dangling as of `2aa5f1ec` — a one-word fix if it bothers you, not worth its own change. Keeping `FOLLOW_UPS.md` is the right call while that code comment exists; whatever deletes it later has to deal with the comment too.

## Proposed change

```bash
cd /Users/alex/Work/codalens/nglspn/nglspn-hq
jj new -m "Drop FRONT_END_REVIEW.md; its findings are closed or in FOLLOW_UPS"

rm FRONT_END_REVIEW.md

jj status        # expect: D FRONT_END_REVIEW.md, nothing else
jj diff --stat
```

That is the whole change. No `.gitignore` entry — this was a deliberate commit, not an escaped artifact, and a rule would only mask a future one.

Before deleting, one check worth thirty seconds: `FRONT_END_REVIEW.md` is 301 lines of findings. Confirm nothing in it is still open and unrecorded elsewhere:

```bash
grep -nE "^(- \[ \]|Open|TODO|Not done|Won't)" FRONT_END_REVIEW.md
```

Anything that comes back and is not already an item in `FOLLOW_UPS.md` needs moving there first. `678dc07e` ("Front-end review fixes") claims the round was applied, and `review/00-SUMMARY.md` records that every blocker the branch's own review rounds raised is genuinely closed — but the grep is cheaper than trusting that.

## The `review/` directory — same question, same answer

`review/` is now tracked. It was added in `2aa5f1ec`, whose own commit message says **"Add additional review (temp - will be removed)"**. So the intent is already recorded; it just has not happened.

Six files, all working notes of the same kind as the file being deleted here:

```
review/00-SUMMARY.md
review/01-features-articles.md
review/02-features-follows-notifications.md
review/03-backend-review.md
review/04-frontend-review.md
review/05-crosscutting-review.md
```

Plus `review/feedback/` — this document and its siblings.

**Recommendation: do not merge `review/` to `main`.** It is working notes, not product, and `docs.md` is explicit about where a review's durable output belongs:

> **OpenSpec changes** — `openspec/changes/<name>/` — the plan of record while work is in flight.

`openspec/changes/add-article-authoring/feedback.md` already exists and is exactly the right home. `simplify-follow-and-cadence/` has no `feedback.md` and could take one.

Concretely, before merge:

1. Fold anything durable out of `review/` and `review/feedback/` into
   `openspec/changes/add-article-authoring/feedback.md` and
   `openspec/changes/simplify-follow-and-cadence/feedback.md`. In practice that
   is the accepted fix proposals — the feature maps in `01`/`02` and the
   verification logs in `05` are session artefacts with no readership after merge.
2. Anything that stays open and does not belong to a change becomes an item in
   `FOLLOW_UPS.md`.
3. Then drop the directory:

   ```bash
   jj new -m "Drop the temporary review directory"
   rm -rf review
   ```

   or, if the whole review lives in its own jj change and nothing else does,
   abandon it: `jj abandon <change-id>`.

Doing this in the same change as the `FRONT_END_REVIEW.md` deletion would be self-defeating — you would delete the document containing the instructions. Do the `FRONT_END_REVIEW.md` deletion now, the `review/` cleanup last, once every proposal in `review/feedback/` has been actioned or rehomed.

`QUESTIONS.md` (226 lines) and the pattern generally — `BEFORE_RELEASE.md` was dropped in `beaa3915` when `REVIEW.md` replaced it — say this is a recurring habit rather than a one-off. Not a finding, just the reason the taxonomy in `docs.md` exists.

## Tests

None applicable — no code, no build input.

```bash
# nothing references the deleted file outside the temporary review directory
grep -rn "FRONT_END_REVIEW" --exclude-dir=.git --exclude-dir=.jj \
  --exclude-dir=node_modules --exclude-dir=review .
# expect: no output

# the build is unaffected
cd src/web-ui && make lint && make test
```

## Risks and what this does not cover

- **Loss of the record.** `FRONT_END_REVIEW.md` documents a real review round and the reasoning behind several fixes. It stays reachable at `4420ffd1` and its fixes at `678dc07e`, and both commit messages name it. That is adequate provenance for working notes. If any of that reasoning is load-bearing for future maintainers, it belongs in a code comment or `openspec/changes/add-article-authoring/feedback.md`, not in a root-level markdown file — moving it is the pre-deletion grep above.
- **`FOLLOW_UPS.md:107` already dangles**, pointing at the deleted `REVIEW.md`. Not caused by this change; fix it whenever `FOLLOW_UPS.md` is next edited.
- **This does not address `QUESTIONS.md`.** Out of scope, and it predates this branch.
- **The `review/` recommendation is a recommendation.** If you would rather keep it, the honest thing is to move it under `docs/` with a date prefix per `docs.md`'s convention (`docs/2026-08-07-article-branch-review.md`) rather than leave a `review/` directory at the root that contradicts the taxonomy the repo just wrote down for itself.
