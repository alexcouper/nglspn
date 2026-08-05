## Context

Follow-ups to a review of the `democratic-ranking` branch. See [proposal.md](proposal.md) for the summary; each finding is worked through below as problem → solution → alternatives.

The branch is otherwise sound: no model changes so no migration, `backend-openapi.json` regenerates with no diff, and the pure tally functions in [`services/review/tally.py`](../../../src/django-backend/services/review/tally.py) are correct — the Schulze initialisation over positive margins is equivalent to the standard `d[a][b] > d[b][a]` form, and win-count tiering is well-defined because the Schulze relation is transitive.

Findings 1–5 are code. Finding 6 is branch hygiene and ships as a rebase.

## Goals / Non-Goals

**Goals:**

- A reviewer never ends up with a locked review that disagrees with what they last saw on screen.
- The service boundary the branch introduced holds at every edge, not most of them.
- Anything the ballot response carries has a reader.

**Non-Goals:**

- Reworking autosave into an optimistic-with-retry queue. The failure is at submit time; that is where the guard goes.
- Offline support or local persistence of an unsaved ballot.
- Revisiting the tally, the pool ordering, or the ballot layout — all reviewed and correct.

## Decisions

### 1. A failed ballot write aborts submission

**Problem.** `saveNow` catches every failure into `setSaveError` and resolves normally ([`MyRanking.tsx:158-171`](../../../src/web-ui/src/app/competitions/[id]/MyRanking.tsx)). `flushPendingSave` awaits it, so it cannot reject. `handleSubmit` then runs:

```ts
await flushPendingSave();
await api.myReview.updateStatus(competitionId, "completed");
setReviewStatus("completed");
```

A reviewer reorders, clicks Submit, the PUT fails — network blip, 400, a session that expired mid-request — and the review flips to `completed` against the *previously saved* ballot. The reviewer sees a "Failed to save rankings" banner next to a submitted, read-only ballot, with no indication that the two are inconsistent. They can reopen the review, but nothing tells them they need to.

The narrow failure here is not the swallowed error — autosave genuinely should not throw at a user mid-drag. It is that submission treats "flush returned" as "flush succeeded".

**Solution.** `saveNow` returns `Promise<boolean>` and `flushPendingSave` propagates it. `handleSubmit` bails before `updateStatus`:

```ts
if (!(await flushPendingSave())) {
  setStatusError("Your ranking could not be saved, so it was not submitted. Try again.");
  return;
}
```

The dialog stays open, the review stays `in_progress`, the ballot stays editable, and Submit is retryable. Autosave's own behaviour is unchanged — `persistOrder` still calls `void saveNow(ids)` and still only surfaces `saveError`.

**Alternatives considered:**

- *Have `saveNow` throw and let `handleSubmit`'s existing `catch` set `statusError`* — fewer moving parts, but it makes the autosave path throw into a floating promise, and the message a reviewer sees ("Failed to submit ranking") would misdescribe a save failure. A boolean keeps the two paths' error copy distinct.
- *Retry the save once before giving up* — hides a real failure behind latency and still needs the guard for the second failure. Worth doing only if we see this happen in practice.
- *Disable Submit while `saveError` is set* — does not help, because the failing write is the one the flush is about to issue; there is no error to observe yet at the moment Submit is pressed.

### 2. Ballot image resolution moves into the query layer

**Problem.** [`api/routers/my_review.py:26-28`](../../../src/django-backend/api/routers/my_review.py):

```python
from services.project.django_impl.query import (
    _variant_url,
    resolve_image_by_purpose,
)
```

A router reaching into another domain's `django_impl` module, for a leading-underscore function with no stability contract. The branch's design doc states the goal as "ballot reads, ballot writes and the tally all go through `services/review/`. No router or admin view touches `ProjectRanking` directly" — this satisfies the letter and not the point. Discover does not do this: `to_discover_item` resolves the URLs inside the query module and the router only ever sees a [`DiscoverProjectItem`](../../../src/django-backend/services/project/query_interface.py).

**Solution.** Follow the discover pattern. `ReviewerProjects.ranked` / `.pool` become lists of a `ReviewProjectItem` dataclass carrying `project`, `hero_banner_url`, `in_use_image_url` and `category_name`. `DjangoReviewQuery.get_reviewer_projects` does the resolution — it already owns the `upload_status="uploaded"` prefetch that makes the resolution correct, so the two live together instead of one relying on the other from across a package boundary. `_project_response` becomes a field mapping.

`get_competition_tally` keeps returning `Project` rows; the admin template reads only `title` and `pk`, and there is no image work to hoist.

**Also done:** `_variant_url` is renamed to `variant_url`. Moving the call into `services/review/django_impl/query.py` fixes the layering but still imports a private symbol across packages — and [`services/follows/django_impl/query.py:12`](../../../src/django-backend/services/follows/django_impl/query.py) already did the same. Three service impls sharing it makes it public API in fact; the name should say so.

**Alternatives considered:**

- *Rename `_variant_url` to `variant_url` and leave the call site* — one character of work, and it does resolve the private-symbol half. But the router would still run image-resolution logic, and the comment in `_project_response` explaining that resolution depends on the *query's* prefetch stays true and stays fragile: the invariant is asserted in one module and enforced in another. Rejected as the *whole* fix; done alongside the move.
- *Duplicate the two helpers into `services/review/`* — two copies of a fallback chain that must agree with discover forever, for no gain.
- *Expose them via `REPO.project`* — makes the router's cross-domain call explicit but keeps per-project resolution in the request handler, which is where the N+1 risk lives.

### 3. Drop `main_image_url` and `main_image_variants` from the ballot response

**Problem.** [`api/schemas/my_review.py:49-50`](../../../src/django-backend/api/schemas/my_review.py) still carries both. `ranking-project-tiles` kept them deliberately, justified as "[`CompetitionReveal.tsx:228`](../../../src/web-ui/src/app/competitions/[id]/CompetitionReveal.tsx) and the reviewer project-detail page still read them" — but `CompetitionReveal.tsx:226` (`WinnerCard`) and `:270` (`ProjectCard`) both take `CompetitionProject`, a different schema, and the detail page uses `ReviewProjectDetailResponse`, also different. Nothing reads them off `ReviewProject`. The ballot renders `in_use_image_url || hero_banner_url`.

So every ballot response carries a variant list per project that no client touches, and the design doc gives a future reader a reason to keep it that does not survive checking.

**Solution.** Remove both fields, regenerate the contract, and drop them from `makeReviewProject` in [`test/factories.ts`](../../../src/web-ui/src/test/factories.ts). Fix the claim in `ranking-project-tiles/proposal.md` rather than leaving a wrong justification in the archive.

**Alternatives considered:**

- *Keep the fields, correct the doc* — defensible; the payload is small and something may want a main image later. Rejected because "small unread field plus a note explaining it is unread" is how responses accumulate, and re-adding a field is a regeneration, not a migration.
- *Keep `main_image_url`, drop the variant list* — splits the difference and leaves the same question for the next reader.

### 4. One home for `EXCLUDED_PROJECT_STATUSES`

**Problem.** Defined identically in [`api/routers/my_review.py:40`](../../../src/django-backend/api/routers/my_review.py) and [`services/review/django_impl/query.py:31`](../../../src/django-backend/services/review/django_impl/query.py). The router copy is still live for its other endpoints, so a status added to one and not the other silently makes the ballot and the reviewer's project list disagree about what is rankable.

**Solution.** Delete the router's copy; import the service's. It is the definition the handler validates against in `replace_ballot`, so it is the one that decides what a reviewer can actually rank.

**Alternatives considered:**

- *Move it to `apps/projects/models.py` next to `ProjectStatus`* — arguably the most natural home, and it would serve any future consumer. Rejected as a wider blast radius than this change needs; worth doing if a third caller appears.

### 5. The tabs get real tab semantics

**Problem.** [`MyRanking.tsx:282`](../../../src/web-ui/src/app/competitions/[id]/MyRanking.tsx) is a `role="tablist"` of `role="tab"` buttons with `aria-selected`, but the panels at `:299` and `:321` are plain `div`s — no `role="tabpanel"`, no `id`, no `aria-controls`, no `aria-labelledby` — and there is no arrow-key handling. A screen reader announces "tab, 1 of 2, selected" and then has nothing to navigate to; keyboard users get Tab-through-every-button instead of the arrow-key behaviour the role promises. The ARIA is a claim the markup does not honour, which is worse than no ARIA.

This matters more than usual here: reviewers are the one group the site actively asks to do careful work, and the tabs are the only route to the unranked pool below `lg`.

**Solution.** Wire the pattern properly — `id` on each tab, `aria-controls` pointing at the panel, `role="tabpanel"` + `aria-labelledby` on each panel, `tabindex="-1"` on the unselected tab (roving tabindex), and Left/Right/Home/End handling on the tablist.

**Alternatives considered:**

- *Drop the ARIA and use plain buttons* — honest, smaller, and a screen reader would describe exactly what is there. Rejected because the tab pattern is genuinely what this is, and the panels are already conditionally rendered per tab; the remaining work is attributes, not structure.
- *Render both panels always and hide one with CSS* — no, `hidden lg:block` is already doing that at `lg` and a hidden tabpanel needs the `hidden` attribute, not just a class, to leave the accessibility tree.

### 6. The Discord URL change moves to its own branch

**Problem.** `SITE_DISCORD_URL` and its four call sites (`lib/constants.ts`, `Footer.tsx`, `about/contact/page.tsx`, `about/prizes/page.tsx`) have nothing to do with ranking. Extracting the constant is a clear improvement, but the invite code itself changes from `D47bQjaQ` to `KX7qmrwP7x` — a live, user-facing link that anyone reviewing a ranking branch will scroll past. If the new invite is wrong or expires, the fix is buried in a 47-file change.

**Solution.** `jj split` it onto its own branch and merge it separately. It has no dependency on anything else here.

**Alternatives considered:**

- *Leave it and call it out in the PR description* — acceptable if the branch is already being merged; the cost is that the invite change is not independently revertable. Take this option only if splitting turns out to conflict.

## Risks / Trade-offs

- **Blocking submit on a save makes a flaky network more visible** → correct trade. Today the reviewer loses their ordering silently; after this they see a retryable error and keep their ballot.
- **Removing response fields is a contract shrink** → additive-only is the safer default, but nothing reads these, no consumer outside this repo exists, and the regeneration step catches any use `tsc` can see.
- **Turning `ReviewerProjects` into DTOs touches the tally-adjacent code path** → it does not: `get_competition_tally` is a separate method returning `Project` rows and is untouched. The existing `django_assert_max_num_queries(10)` budget on the ballot endpoint guards the query count either way.
- **The `project-ranking-ballot` delta has no base spec to modify yet** → `openspec validate --strict` passes regardless, but the two `MODIFIED` requirements only reconcile against a real base once `less-biased-project-ranking` and then `ranking-project-tiles` are archived. Archive in that order before syncing this change, or the modification lands on requirement text that has since moved.

## Migration Plan

No data migration; no model change. Backend and frontend ship together because the response shape shrinks — regenerate `backend-openapi.json` and run `npm run generate-types` (see [CONTRIBUTING.md](../../../CONTRIBUTING.md)).

Rollback is a revert. No stored data depends on any of this.

## Open Questions

- **Should the submit failure distinguish "not saved" from "saved but not submitted"?** `updateStatus` can fail on its own, and the reviewer's next action differs: retry Submit versus check the ballot first. One message for both is simpler and probably enough at this scale.
- **Is the new Discord invite permanent?** `discord.gg` codes expire unless the invite was created as never-expiring. Worth confirming before the split branch merges — the whole point of the constant is that there is one place to fix it.
