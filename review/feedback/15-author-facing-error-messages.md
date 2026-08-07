# 15. Author-facing error messages

**Finding:** Minor (frontend B5) — raw API-layer error strings are shown verbatim to authors; a backend blip during Save puts "Token refresh failed" in red next to the button.

**Alex:** "What do you suggest?"

**Type:** fix proposal

**Effort:** S — one new 30-line file, two error classes in `base.ts`, four call sites, about six tests. Half a day including the tests.

## Correcting the premise on language

The brief for this document said the product is Icelandic and the copy should be too. It is not, in the UI. I checked: the only Icelandic strings in `src/web-ui/src` are the wordmark and the layout metadata tagline — `app/layout.tsx:32-33` (`"naglasúpan"`, `"Byggjum, deilum, vöxum saman"`), `components/Navigation.tsx:58,66,120`, and the brand name inside otherwise-English prose in `app/privacy/page.tsx` and `app/about/why/page.tsx`. Every one of the ~40 error strings in the app is English: "Failed to save article", "Couldn't load followed projects", "Couldn't update channel". There is no i18n infrastructure — no locale files, no `next-intl`, nothing under `src/lib`.

So the copy below is English. Introducing three Icelandic error strings here would make them the only Icelandic user-facing text in the product outside the wordmark, and would be a worse experience than the English they replace. If Icelandic is the intent, that is a product-wide decision that needs translation infrastructure and a pass over the whole UI — not something to smuggle in through an error handler. Say the word and it is a separate piece of work.

## What is actually happening

`draft.error` renders at `ArticleAuthoringPage.tsx:170-174`, in red, next to the Save button. Five distinct classes of string can land there via `useArticleDraft.ts:141` (load), `:287` (save), `:347` (delete) and `:331-333` (publish's non-422 branch).

**1. `"Token refresh failed"` — `lib/api/base.ts:143`.** The request 401'd, `attemptTokenRefresh` was called, and it returned `"transient"` — meaning the refresh endpoint answered non-401-not-ok, or `fetch` threw (`base.ts:86-94`). **The author is not logged out.** The tokens are deliberately kept (`base.ts:140-142`), no `auth:logout` is dispatched, and the next request will succeed once the backend or the connection recovers. What failed is this one request. Correct advice: try again.

**2. `"Unauthorized"` — `base.ts:137` and `:151`.** The refresh endpoint returned 401, or a retried request still 401'd. Here `clearTokens()` has already run and `auth:logout` has already been dispatched. `contexts/auth.tsx:51-53` sets `user` to null; `useRequireAuth:13-14` then pushes `buildLoginPath(pathname)`. **The author genuinely is logged out and is already being redirected.** Anything this handler writes into `error` is a flash before the route changes.

**3. `ApiRequestError.message` — `base.ts:158`, `= error.detail || "Request failed"`.** These are the strings worth showing. From the article PATCH path (`api/routers/articles.py:161-174`): "Article not found", "Channel not found on this project", "Listing image must belong to this project", "Listing image upload has not completed", "Image framing is not a valid crop of this image". They tell the author something actionable. `"Request failed"` is the fallback and tells them nothing.

**4. A `fetch` rejection.** `base.ts:120` is unguarded, so an offline or DNS failure throws a `TypeError` whose message is browser-specific and reaches the UI verbatim: "Failed to fetch" (Chrome), "Load failed" (Safari), "NetworkError when attempting to fetch resource" (Firefox).

**5. A `SyntaxError` from `base.ts:155`.** `await response.json()` runs inside the `!response.ok` branch with no guard. A 502 from a proxy is an HTML page, so the author sees `Unexpected token '<', "<html>"... is not valid JSON` — which reads like a bug in our client, because in a sense it is.

Only class 3 is written for a human who is not a developer. The other four are diagnostics.

`publish()` (`useArticleDraft.ts:324-329`) is the in-repo pattern: it narrows on `ApiRequestError`, pulls `err.body.detail` when the status is 422, and falls back to a fixed sentence. It is right, and it is one branch of what the shared function below does.

## Proposed change

### Where it lives

Three options.

**Option A — a shared `describeApiError` in `src/web-ui/src/lib/api/errors.ts`, plus two named error classes in `base.ts`. Recommended.**

**Option B — map at each of the four call sites.** Loses: four copies of the same table, and the next handler to be written will not get a copy.

**Option C — have `base.ts` throw already-human strings.** Loses: it destroys the distinction. `"Token refresh failed"` and `"Unauthorized"` are load-bearing *for developers* and appear in `base.test.ts:81,93,150`. The API layer should keep saying what happened; the UI layer decides what a person is told. Also blast radius: every `err.message` consumer app-wide shifts text at once.

### The change, concretely

`lib/api/base.ts` — replace the three bare throws with two named classes. Messages are unchanged, so nothing that reads `err.message` shifts and `base.test.ts`'s `rejects.toThrow("Unauthorized")` assertions stay green:

```ts
// The refresh outcome matters to callers, not only to this file. "transient"
// means the credentials are still good and a retry will work; "invalid" means
// the session is over and the redirect to /login is already in flight. The
// messages are unchanged — they are for whoever is reading the console.
export class AuthTransientError extends Error {
  constructor() {
    super("Token refresh failed");
  }
}

export class AuthExpiredError extends Error {
  constructor() {
    super("Unauthorized");
  }
}
```

`:137` and `:151` throw `new AuthExpiredError()`; `:143` throws `new AuthTransientError()`.

Second, small, hunk at `:155` so class 5 stops happening:

```diff
     if (!response.ok) {
-      const body = await response.json();
+      // A 502 from the proxy is an HTML page, and an unguarded json() would
+      // throw a SyntaxError that reads to the author like a client bug.
+      const body = await response.json().catch(() => ({}));
       const error = body as ApiError;
```

New file `lib/api/errors.ts`:

```ts
import { ApiRequestError, AuthExpiredError, AuthTransientError } from "./base";

// The backend's `detail` is written for the person reading it. A thrown
// Error's message is written for whoever is reading the console. Only the
// first kind gets shown to an author.

const UNREACHABLE =
  "Couldn't reach the server. Nothing was sent — your work is still here. Try again.";
const SESSION_ENDED = "Your session has ended. Sign in again to continue.";
const SERVER_FAULT =
  "Something went wrong at our end. Nothing was saved — try again in a moment.";

export function describeApiError(err: unknown, fallback: string): string {
  // Not logged out: base.ts deliberately keeps the tokens on a transient
  // refresh failure, so telling the author to sign in again would be wrong.
  if (err instanceof AuthTransientError) return UNREACHABLE;
  // Logged out, and useRequireAuth is already routing to /login. This is a
  // flash, so it only has to be true.
  if (err instanceof AuthExpiredError) return SESSION_ENDED;
  if (err instanceof ApiRequestError) {
    if (err.status >= 500) return SERVER_FAULT;
    // Read `body.detail` rather than `err.message`, which falls back to the
    // useless "Request failed".
    return typeof err.body.detail === "string" ? err.body.detail : fallback;
  }
  // fetch() rejects with a TypeError when the network is gone.
  if (err instanceof TypeError) return UNREACHABLE;
  return fallback;
}
```

Call sites in `useArticleDraft.ts`:

```diff
-        setError(err instanceof Error ? err.message : "Failed to load article");
+        setError(describeApiError(err, "Couldn't open this article."));
```
```diff
-        setError(err instanceof Error ? err.message : "Failed to save article");
+        setError(describeApiError(err, "Couldn't save this article."));
```
```diff
-      setError(err instanceof Error ? err.message : "Failed to delete article");
+      setError(describeApiError(err, "Couldn't delete this article."));
```

And `publish()` at `:323-334` collapses, because `describeApiError` already extracts `body.detail` for any 4xx — the 422 branch was a special case of it:

```diff
     } catch (err) {
-      if (err instanceof ApiRequestError && err.status === 422) {
-        const detail =
-          typeof err.body.detail === "string"
-            ? err.body.detail
-            : "Article is not ready to publish.";
-        setError(detail);
-      } else {
-        setError(
-          err instanceof Error ? err.message : "Failed to publish article",
-        );
-      }
+      setError(describeApiError(err, "Article is not ready to publish."));
       setIsPublishing(false);
     }
```

The `ApiRequestError` import at `useArticleDraft.ts:13` then goes away.

### The copy, in full

| Case | Shown to the author |
|---|---|
| Transient refresh failure, or the network is gone | Couldn't reach the server. Nothing was sent — your work is still here. Try again. |
| Session genuinely expired | Your session has ended. Sign in again to continue. |
| 5xx | Something went wrong at our end. Nothing was saved — try again in a moment. |
| 4xx with a `detail` | the backend's `detail`, unchanged |
| Load fallback | Couldn't open this article. |
| Save fallback | Couldn't save this article. |
| Delete fallback | Couldn't delete this article. |
| Publish fallback | Article is not ready to publish. |

"Nothing was sent — your work is still here" is the sentence that matters. The author's real question at that moment is "did I just lose the last twenty minutes", and for the transient and network cases the answer is a definite no.

## Tests

New `src/web-ui/src/lib/api/errors.test.ts`:

- tells the author to retry when the token refresh failed transiently
- does not claim the session ended when the tokens were kept
- says the session ended when the credentials were actually rejected
- passes a backend `detail` through unchanged
- hides a 5xx `detail` behind a neutral sentence
- treats a network `TypeError` as unreachable rather than as a bug
- falls back to the caller's sentence for anything unrecognised

`src/lib/api/base.test.ts` — one addition: the transient path throws `AuthTransientError` and leaves the tokens in place. The existing message-based assertions at `:81,93,150` need no change; that is the point of keeping the messages.

`use-article-draft.test.tsx` — the existing `it("surfaces a failure instead of claiming the draft was saved")` at `:347` should assert on the mapped sentence rather than the raw one, plus one new case: a transient auth failure during save does not tell the author they are logged out.

## Risks and what this does not cover

- **The transient/invalid split must survive, and this change is where it could quietly die.** `describeApiError` distinguishes them by class, not by string, so the two must not be collapsed into one error type "for tidiness". The comment in `errors.ts` says why; keep it.
- **`instanceof` across module instances.** Vitest module mocking can produce two copies of `base.ts` and break `instanceof`. `use-article-draft.test.tsx:22` already mocks `@/lib/api` wholesale, so if a test constructs an `AuthTransientError` from a different import path the narrowing silently falls through to the fallback string. Import the classes from `@/lib/api/base` in tests, not from a mock.
- **The rest of the app is untouched.** Roughly thirty other `err instanceof Error ? err.message : "Failed to …"` sites (`ProjectDetail.tsx`, `ProjectsList.tsx`, `profile/page.tsx`, `login/page.tsx`, …) have the same defect. `describeApiError` is the seam to convert them through, one file at a time. Not part of this change.
- **The genuinely-logged-out case still loses the body.** When `AuthExpiredError` fires, `useRequireAuth` pushes to `/login` and the unsaved body in `bodyRef` goes with it. Better copy does not fix that. It is the same underlying gap as findings I4 and I5 — the body only exists in memory — and it is a separate piece of work.
- **Backend `detail` strings are the author-facing copy now, explicitly.** "Image framing is not a valid crop of this image" is passable; anything added to `_PATCH_ARTICLE_ERRORS` from now on is UI text and should be written that way. Worth a line in the review checklist.
