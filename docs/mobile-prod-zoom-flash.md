# Mobile prod-only zoom + flash on projects page

## Symptoms (mobile Safari, production build, authenticated)

1. After login, page is slightly over-zoomed — user has to zoom out to see full width.
2. Leaving the projects page and returning: it renders very small for a beat, flashes, then snaps to fullscreen.

Neither symptom reproduces under `make dev`. Both reproduce against `make run-non-dev` (prod build via `next start`).

## Suspected causes

### 1. No explicit `viewport` export in `src/web-ui/src/app/layout.tsx`

`metadata` is exported but `viewport` is not. Next.js 13+ split these; the default is normally injected, but it's not guaranteed in every build path, and missing `width=device-width, initial-scale=1` is exactly what causes mobile Safari to pick its own zoom.

### 2. FOUC in prod that doesn't exist in dev

- In dev, Tailwind CSS is injected via JS.
- In prod (Tailwind v4 + `@tailwindcss/postcss`), CSS ships as a separate `<link>` file.
- On mobile, HTML paints before CSS arrives →
  `min-h-screen`, `max-w-6xl`, `flex`, `md:*` responsive classes aren't applied →
  page renders as narrow unstyled flow → Safari scales down → "renders really small" →
  CSS arrives → layout snaps to fullscreen → the flash.

### 3. Auth hydration amplifies the flash

`src/web-ui/src/contexts/auth.tsx:29-42` starts `isLoading: true` and flips after `getCurrentUser()`. `Navigation` renders different link sets / `UserMenu` depending on loading+auth state, so authed users get an extra layout pass right at hydration — worst-case moment combined with (1) and (2), and why symptoms only show when authenticated.

## Plan

### Investigation

1. Reproduce on phone against `make run-non-dev`. ✅ Confirmed.
2. Inspect live page via Safari Develop menu → iPhone → [tab].
3. Check `<head>` for `<meta name="viewport">`. If missing/wrong, suspect 1 confirmed.
4. In Network tab, check whether the main CSS `<link>` blocks paint or loads late. Note timing.
5. Toggle "Disable JS" in Safari and reload. If symptoms disappear with JS off, hydration (suspect 3) is contributing; if they persist, it's pure CSS-loading (suspect 2).

### Fix, in priority order

1. **Add explicit `viewport` export** in `src/web-ui/src/app/layout.tsx`:
   ```ts
   import type { Viewport } from "next";
   export const viewport: Viewport = { width: "device-width", initialScale: 1 };
   ```
   Rebuild, reload on phone. Expect the over-zoom to disappear.

2. **If flash remains**, inspect the built HTML for the CSS `<link>` — confirm it's in `<head>` and not lazy/`media`-swapped. Next 16 + Tailwind v4 should put it there; if not, that's the cause.

3. **If flash is tied to auth hydration** (step 5 showed JS matters), reduce layout shift in `src/web-ui/src/components/Navigation.tsx` by reserving space for the auth area while `isLoading` — render a fixed-width placeholder in both `isLoading` and authed states so the nav doesn't reflow.

### Verify

- Rebuild, retest on phone. Both symptoms gone.
- Sanity-check desktop and tablet widths haven't regressed.

## Reproduction tooling

`src/web-ui/Makefile` → `make run-non-dev` (script at `src/web-ui/scripts/run-non-dev.sh`) builds the prod bundle, performs the same CSP/URL placeholder substitutions as the container's `entrypoint.sh`, and serves on `0.0.0.0:3000` for LAN phone testing. Override `API_URL`, `CDN_URL`, `HOST`, `PORT` as needed.
