# Phase 2 — Web-UI Bilingual Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve the Naglasúpan web-ui in two locales — Icelandic at `/` (default) and English at `/en/*` — with the Icelandic catalog loaded from Django at request time via `next-intl`, cached with `unstable_cache`, and invalidated seconds after an edit through a webhook from Django.

**Architecture:** All routes move under a `[locale]` segment. `next-intl` middleware performs locale negotiation (cookie → `Accept-Language` → default `is`) and rewrites URLs so the default locale is un-prefixed. On the server we fetch `GET /api/i18n/<locale>` from Django through a server-only helper wrapped in `unstable_cache` tagged `i18n:<locale>`. English strings also live in `src/messages/en.json` in the repo as the **source of truth for key existence**; the Django catalog for `en` is empty in this phase so English rendering comes from that JSON (Phase 3 seeds Django). Icelandic rendering comes from Django; missing keys fall back to English. A `POST /api/revalidate-i18n` route verifies a shared secret and calls `revalidateTag('i18n:' + locale)`.

**Tech Stack:** Next.js 16 App Router, React 19, `next-intl` (latest v3/v4 App-Router API), TypeScript, Django Ninja backend (Phase 1), Playwright for smoke tests.

**Design reference:** `docs/superpowers/specs/2026-04-22-dynamic-translations-design.md`
**Phase 1 output:** `docs/superpowers/verify.md`

---

## Scope

**In scope (Phase 2):**
- Install and configure `next-intl` with locale-prefixed routing (`as-needed`: no prefix for `is`, `/en` prefix for English).
- Move every `src/app/*` route under `src/app/[locale]/`.
- Request-config wiring + catalog fetcher using `unstable_cache` tagged per locale.
- Root `<html lang>` reflects active locale. `hreflang` alternates emitted for every page via metadata.
- Locale switcher in the existing `Navigation`.
- `/api/revalidate-i18n` route (shared-secret verified).
- Replace hardcoded strings in **Navigation** and **Footer** with `t()` calls as the proof surface. Other pages keep their current hardcoded Icelandic (Phase 4 does the full sweep).
- `en.json` in the repo containing exactly the keys used by Navigation + Footer.
- One hand-written Django data migration in `apps.translations` that seeds the same keys in `is` — enough to render the page end-to-end.
- Playwright smoke test: visit `/`, see Icelandic Navigation text; visit `/en`, see English; edit the DB, trigger revalidate webhook, reload, see updated text.

**Out of scope (later phases):**
- `<Translatable>` wrapper, pencil-on-hover, inline popover, history (Phase 4).
- `make translate-new-keys` MT generator + pre-push lint (Phase 3).
- Editor worklist (Phase 5).
- Replacing hardcoded strings in non-chrome pages (Phase 4 sweep).
- Splitting `en.json` into server-only vs client messages (fast-follow per design §Payload size).

## File structure

**Create:**
- `src/web-ui/src/i18n/config.ts` — Locale constants, default locale, list of supported locales, type alias.
- `src/web-ui/src/i18n/routing.ts` — `next-intl` `defineRouting` config (shared between middleware, navigation helpers, and request config).
- `src/web-ui/src/i18n/navigation.ts` — Re-exports `Link`, `redirect`, `usePathname`, `useRouter`, `getPathname` from `next-intl/navigation` bound to our routing config.
- `src/web-ui/src/i18n/request.ts` — `next-intl` request config (`getRequestConfig`) that resolves messages per request by merging `en.json` (fallback) with the Django catalog for the active locale.
- `src/web-ui/src/lib/i18n/catalog.ts` — Server-only `fetchCatalog(locale)` using `unstable_cache` tagged `i18n:<locale>`, revalidate 60s.
- `src/web-ui/src/messages/en.json` — English source catalog (Navigation + Footer keys only for Phase 2).
- `src/web-ui/src/middleware.ts` — Wraps `next-intl` middleware, with matcher excluding `/api`, `/_next`, static files.
- `src/web-ui/src/app/api/revalidate-i18n/route.ts` — POST handler: verifies `X-Revalidate-Secret` header, calls `revalidateTag`.
- `src/web-ui/src/app/[locale]/layout.tsx` — Per-locale layout wrapping children in `NextIntlClientProvider` with messages from `getMessages()`; sets `<html lang={locale}>`.
- `src/web-ui/src/components/LocaleSwitcher.tsx` — Client component that toggles between `is`/`en` using `next-intl` navigation.
- `src/django-backend/apps/translations/migrations/0003_seed_phase2_ui_chrome.py` — Hand-written data migration seeding `is` rows for Navigation + Footer keys.
- `src/web-ui/e2e/i18n.spec.ts` — Playwright smoke test.

**Modify:**
- `src/web-ui/src/app/layout.tsx` — Remove per-locale concerns, keep only font + Plausible + base html shell; delegate body content to `[locale]/layout.tsx`.
- `src/web-ui/src/components/Navigation.tsx` — Replace hardcoded strings with `useTranslations('nav')`; swap `next/link` and `next/navigation` imports for `@/i18n/navigation`.
- `src/web-ui/src/components/Footer.tsx` — Same pattern with `useTranslations('footer')`.
- `src/web-ui/src/components/UserMenu.tsx` — Swap `next/link` import for `@/i18n/navigation` (so active-locale links work); no string changes.
- `src/web-ui/next.config.ts` — Wrap export in `createNextIntlPlugin('./src/i18n/request.ts')(...)`.
- `src/web-ui/package.json` — Adds `next-intl` dependency.
- `src/web-ui/.env.claude` (only if present) — Add `WEB_UI_REVALIDATE_SECRET` for Playwright test; otherwise document in `README.md`.
- **All existing route directories under `src/app/`** — moved under `src/app/[locale]/`:
  - `about/`, `competitions/`, `login/`, `my-projects/`, `my-reviews/`, `old/`, `onboarding/`, `privacy/`, `prizes/`, `profile/`, `projects/`, `register/`, `submit/`, `users/`, `verify-email/`, `why/`, `page.tsx`, `globals.css` stays at `src/app/`.
  - `health/` stays at `src/app/health/` (not locale-dependent; health checks must work without locale).
  - `icon.png` stays at `src/app/`.
  - `api/` (new, for revalidate-i18n) stays at `src/app/api/`.

**Test:**
- `src/web-ui/e2e/i18n.spec.ts`

---

## Environment variables

Add to `src/web-ui`:
- `WEB_UI_REVALIDATE_SECRET` — same value as the Django side (`WEB_UI_REVALIDATE_SECRET`). Must be set in the web-ui process for the revalidate route to accept webhook calls.

Already in use on the Django side (Phase 1):
- `WEB_UI_REVALIDATE_URL` — set to `http://localhost:3000/api/revalidate-i18n` locally.
- `WEB_UI_REVALIDATE_SECRET` — shared with web-ui.

---

## Task 1: Install dependencies

**Files:**
- Modify: `src/web-ui/package.json`
- Modify: `src/web-ui/package-lock.json`

- [ ] **Step 1: Install next-intl**

Run:
```bash
cd src/web-ui
npm install next-intl
```

Expected: `next-intl` appears in `dependencies`. Exit 0.

- [ ] **Step 2: Verify install**

Run: `cd src/web-ui && node -e "console.log(require('next-intl/package.json').version)"`
Expected: prints a version (≥3.x). Exit 0.

- [ ] **Step 3: Commit**

```bash
cd /Users/alex/Work/codalens/nglspn/nglspn-w1
jj new -m "feat(web-ui): install next-intl"
jj commit -m "feat(web-ui): install next-intl"
```

---

## Task 2: Routing config + locale constants

**Files:**
- Create: `src/web-ui/src/i18n/config.ts`
- Create: `src/web-ui/src/i18n/routing.ts`
- Create: `src/web-ui/src/i18n/navigation.ts`

- [ ] **Step 1: Start a changeset**

```bash
cd /Users/alex/Work/codalens/nglspn/nglspn-w1
jj new -m "feat(web-ui): i18n routing config + navigation helpers"
```

- [ ] **Step 2: Write `src/web-ui/src/i18n/config.ts`**

```ts
export const locales = ["is", "en"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "is";

export const localeLabels: Record<Locale, string> = {
  is: "Íslenska",
  en: "English",
};
```

- [ ] **Step 3: Write `src/web-ui/src/i18n/routing.ts`**

```ts
import { defineRouting } from "next-intl/routing";
import { locales, defaultLocale } from "./config";

export const routing = defineRouting({
  locales: [...locales],
  defaultLocale,
  localePrefix: "as-needed",
  localeDetection: true,
});
```

- [ ] **Step 4: Write `src/web-ui/src/i18n/navigation.ts`**

```ts
import { createNavigation } from "next-intl/navigation";
import { routing } from "./routing";

export const { Link, redirect, usePathname, useRouter, getPathname } =
  createNavigation(routing);
```

- [ ] **Step 5: Typecheck**

Run: `cd src/web-ui && npx tsc --noEmit`
Expected: no errors involving the new files.

- [ ] **Step 6: Commit**

```bash
jj commit -m "feat(web-ui): i18n routing config + navigation helpers"
```

---

## Task 3: Catalog fetcher (server-only, cached, tagged)

**Files:**
- Create: `src/web-ui/src/lib/i18n/catalog.ts`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(web-ui): Django translation catalog fetcher"
```

- [ ] **Step 2: Write `src/web-ui/src/lib/i18n/catalog.ts`**

```ts
import "server-only";
import { unstable_cache } from "next/cache";
import type { Locale } from "@/i18n/config";

const API_URL =
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

export type Catalog = Record<string, string>;

async function fetchCatalogFresh(locale: Locale): Promise<Catalog> {
  const res = await fetch(`${API_URL}/api/i18n/${locale}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    console.warn(`[i18n] Failed to load catalog for ${locale}: ${res.status}`);
    return {};
  }
  return (await res.json()) as Catalog;
}

export const fetchCatalog = (locale: Locale): Promise<Catalog> =>
  unstable_cache(
    () => fetchCatalogFresh(locale),
    ["i18n", locale],
    { tags: [`i18n:${locale}`], revalidate: 60 },
  )();
```

- [ ] **Step 3: Typecheck**

Run: `cd src/web-ui && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
jj commit -m "feat(web-ui): Django translation catalog fetcher (unstable_cache + tag)"
```

---

## Task 4: English seed catalog

**Files:**
- Create: `src/web-ui/src/messages/en.json`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(web-ui): seed en.json for Navigation + Footer"
```

- [ ] **Step 2: Write `src/web-ui/src/messages/en.json`**

Include only keys that will be referenced in Task 10 and Task 11. Actual strings should match what currently appears in `src/components/Navigation.tsx` and `src/components/Footer.tsx` verbatim (read those files first to copy the English originals; if the current content is Icelandic, write the English translation of it).

Shape:

```json
{
  "nav": {
    "home": "Home",
    "projects": "Projects",
    "competitions": "Competitions",
    "why": "Why",
    "about": "About",
    "login": "Log in",
    "register": "Register",
    "submit": "Submit a project",
    "myProjects": "My projects",
    "myReviews": "My reviews",
    "profile": "Profile",
    "logout": "Log out"
  },
  "footer": {
    "about": "About",
    "privacy": "Privacy",
    "discord": "Discord"
  }
}
```

Adjust the exact list to match the actual Navigation/Footer link set after reading those two components at the top of Task 10.

- [ ] **Step 3: Commit**

```bash
jj commit -m "feat(web-ui): seed en.json for Navigation + Footer"
```

---

## Task 5: `next-intl` request config

**Files:**
- Create: `src/web-ui/src/i18n/request.ts`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(web-ui): next-intl request config"
```

- [ ] **Step 2: Write `src/web-ui/src/i18n/request.ts`**

```ts
import { getRequestConfig } from "next-intl/server";
import { hasLocale } from "next-intl";
import { routing } from "./routing";
import type { Locale } from "./config";
import { fetchCatalog } from "@/lib/i18n/catalog";
import enMessages from "@/messages/en.json";

// Convert flat dotted-key catalog ({"nav.home": "Heim"}) into the nested shape
// next-intl expects ({nav: {home: "Heim"}}).
function unflatten(flat: Record<string, string>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(flat)) {
    const parts = key.split(".");
    let cursor: Record<string, unknown> = out;
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      if (
        typeof cursor[part] !== "object" ||
        cursor[part] === null ||
        Array.isArray(cursor[part])
      ) {
        cursor[part] = {};
      }
      cursor = cursor[part] as Record<string, unknown>;
    }
    cursor[parts[parts.length - 1]] = value;
  }
  return out;
}

function deepMerge(
  base: Record<string, unknown>,
  over: Record<string, unknown>,
): Record<string, unknown> {
  const result: Record<string, unknown> = { ...base };
  for (const [key, value] of Object.entries(over)) {
    const existing = result[key];
    if (
      typeof value === "object" &&
      value !== null &&
      !Array.isArray(value) &&
      typeof existing === "object" &&
      existing !== null &&
      !Array.isArray(existing)
    ) {
      result[key] = deepMerge(
        existing as Record<string, unknown>,
        value as Record<string, unknown>,
      );
    } else {
      result[key] = value;
    }
  }
  return result;
}

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;
  const locale: Locale = hasLocale(routing.locales, requested)
    ? (requested as Locale)
    : routing.defaultLocale;

  // English: use en.json verbatim (source of truth in code).
  // Icelandic (and any future locale): fetch from Django, fall back to en.json.
  let messages: Record<string, unknown> = enMessages as Record<string, unknown>;
  if (locale !== "en") {
    const djangoCatalog = await fetchCatalog(locale);
    messages = deepMerge(enMessages as Record<string, unknown>, unflatten(djangoCatalog));
  }

  return { locale, messages };
});
```

- [ ] **Step 3: Typecheck**

Run: `cd src/web-ui && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
jj commit -m "feat(web-ui): next-intl request config with Django catalog merge"
```

---

## Task 6: Wire `next-intl` plugin into `next.config.ts`

**Files:**
- Modify: `src/web-ui/next.config.ts`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(web-ui): wire next-intl plugin"
```

- [ ] **Step 2: Edit `next.config.ts`**

At the top of the file add:

```ts
import createNextIntlPlugin from "next-intl/plugin";
const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");
```

Change the final line from:

```ts
export default nextConfig;
```

to:

```ts
export default withNextIntl(nextConfig);
```

- [ ] **Step 3: Typecheck**

Run: `cd src/web-ui && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
jj commit -m "feat(web-ui): wire next-intl plugin into next.config"
```

---

## Task 7: Middleware

**Files:**
- Create: `src/web-ui/src/middleware.ts`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(web-ui): next-intl middleware for locale routing"
```

- [ ] **Step 2: Write `src/web-ui/src/middleware.ts`**

```ts
import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  // Match all paths except API routes, Next internals, static files, and health.
  matcher: ["/((?!api|_next|_vercel|health|.*\\..*).*)"],
};
```

- [ ] **Step 3: Typecheck**

Run: `cd src/web-ui && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
jj commit -m "feat(web-ui): next-intl middleware for locale routing"
```

---

## Task 8: Move all routes under `[locale]`

**Files:**
- Move (rename via filesystem): `src/web-ui/src/app/{about,competitions,login,my-projects,my-reviews,old,onboarding,privacy,prizes,profile,projects,register,submit,users,verify-email,why,page.tsx}` → `src/web-ui/src/app/[locale]/...`
- Keep at `src/web-ui/src/app/`: `layout.tsx`, `globals.css`, `icon.png`, `health/`, `components/` (route-colocated shared bits; leave unless breakage), any future `api/`.

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(web-ui): move routes under [locale] segment"
```

- [ ] **Step 2: Create `[locale]` directory and move route directories + root page**

Run:

```bash
cd src/web-ui/src/app
mkdir -p '[locale]'
for d in about competitions login my-projects my-reviews old onboarding privacy prizes profile projects register submit users verify-email why; do
  [ -e "$d" ] && mv "$d" "[locale]/$d"
done
[ -e page.tsx ] && mv page.tsx '[locale]/page.tsx'
```

Expected: `src/app/[locale]/` contains all the moved directories and `page.tsx`; `src/app/` still contains `layout.tsx`, `globals.css`, `icon.png`, `health/`, `components/`.

- [ ] **Step 3: Verify no route directories remain at `src/app/` that shouldn't**

Run: `ls src/web-ui/src/app/`
Expected output lines (order may vary):
```
[locale]
components
globals.css
health
icon.png
layout.tsx
```

- [ ] **Step 4: Commit**

```bash
jj commit -m "feat(web-ui): move routes under [locale] segment"
```

---

## Task 9: Split root layout into app-root + locale-root

**Files:**
- Modify: `src/web-ui/src/app/layout.tsx`
- Create: `src/web-ui/src/app/[locale]/layout.tsx`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(web-ui): split layout into app-root + per-locale"
```

- [ ] **Step 2: Rewrite `src/web-ui/src/app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { PlausibleTracker } from "@/components/PlausibleTracker";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://naglasupan.is"),
  title: "naglasúpan",
  description: "Byggjum, deilum, vöxum saman",
  icons: {
    icon: [
      { url: "/icons/favicon/favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/icons/favicon/favicon-16.png", sizes: "16x16", type: "image/png" },
    ],
    apple: [{ url: "/icons/favicon/apple-touch-icon.png" }],
  },
  openGraph: {
    title: "naglasúpan",
    description: "Byggjum, deilum, vöxum saman",
    images: [{ url: "/icons/app/logo.png", alt: "naglasúpan" }],
  },
  twitter: {
    card: "summary",
    title: "naglasúpan",
    description: "Byggjum, deilum, vöxum saman",
    images: ["/icons/app/logo.png"],
  },
};

// The <html> element is rendered here with a placeholder lang; the per-locale
// layout overrides it via a rewrite of the tag is not possible, so we keep lang
// on a nested <body> wrapper and rely on per-locale layout for correct metadata.
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html>
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} antialiased min-h-screen flex flex-col`}
      >
        <PlausibleTracker />
        {children}
      </body>
    </html>
  );
}
```

Note: Next.js only allows one `<html>` and `<body>` per render; this stays at the root. The per-locale layout sets locale context but does not re-render `<html>`. To set `lang={locale}` we use a small client-side effect in the per-locale layout (Step 3).

- [ ] **Step 3: Write `src/web-ui/src/app/[locale]/layout.tsx`**

```tsx
import { notFound } from "next/navigation";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";
import { Suspense } from "react";
import { AuthProvider } from "@/contexts/auth";
import { Navigation } from "@/components/Navigation";
import { Footer } from "@/components/Footer";
import { routing } from "@/i18n/routing";
import { hasLocale } from "next-intl";
import { LocaleHtmlLang } from "@/components/LocaleHtmlLang";

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);

  const messages = await getMessages();

  return (
    <NextIntlClientProvider locale={locale} messages={messages}>
      <LocaleHtmlLang locale={locale} />
      <AuthProvider>
        <Suspense>
          <Navigation />
        </Suspense>
        <Suspense>
          <div className="flex-1 flex flex-col">{children}</div>
        </Suspense>
        <Footer />
      </AuthProvider>
    </NextIntlClientProvider>
  );
}
```

- [ ] **Step 4: Write `src/web-ui/src/components/LocaleHtmlLang.tsx`**

```tsx
"use client";
import { useEffect } from "react";

export function LocaleHtmlLang({ locale }: { locale: string }) {
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);
  return null;
}
```

- [ ] **Step 5: Typecheck**

Run: `cd src/web-ui && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
jj commit -m "feat(web-ui): per-locale layout with NextIntlClientProvider"
```

---

## Task 10: Convert Navigation to `t()` + locale-aware Link

**Files:**
- Modify: `src/web-ui/src/components/Navigation.tsx`
- Modify: `src/web-ui/src/components/UserMenu.tsx`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(web-ui): Navigation + UserMenu use next-intl"
```

- [ ] **Step 2: Read current Navigation strings**

Read `src/web-ui/src/components/Navigation.tsx` in full. For each visible English/Icelandic string on a link or button, note the key in `en.json` you'll use (matching Task 4's shape: `nav.home`, `nav.projects`, etc.). If any string is missing from `en.json`, update `en.json` now before continuing — do not add `t()` calls for keys that don't exist in `en.json`.

- [ ] **Step 3: Edit `Navigation.tsx`**

Replace:
```tsx
import Link from "next/link";
import { usePathname } from "next/navigation";
```
with:
```tsx
import { Link, usePathname } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
```

Inside the component, add:
```tsx
const t = useTranslations("nav");
```

Replace every hardcoded link label with `{t("<key>")}`. Keep all other JSX, classes, and behavior identical.

- [ ] **Step 4: Edit `UserMenu.tsx`**

Replace the `next/link` import with `import { Link } from "@/i18n/navigation";`. If `UserMenu` has visible strings, replicate the Navigation pattern with `useTranslations("nav")`. Otherwise leave strings alone.

- [ ] **Step 5: Typecheck + lint**

Run: `cd src/web-ui && npm run lint`
Expected: no new errors.

- [ ] **Step 6: Commit**

```bash
jj commit -m "feat(web-ui): Navigation + UserMenu use next-intl"
```

---

## Task 11: Convert Footer to `t()` + locale-aware Link

**Files:**
- Modify: `src/web-ui/src/components/Footer.tsx`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(web-ui): Footer uses next-intl"
```

- [ ] **Step 2: Edit `Footer.tsx`**

Replace:
```tsx
import Link from "next/link";
```
with:
```tsx
import { Link } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
```

Add `const t = useTranslations("footer");` inside the component and replace each visible label with `{t("<key>")}` matching the keys in `en.json`. External links (Discord) can keep the plain `<a>` element — locale-aware `Link` is only for internal routes.

- [ ] **Step 3: Lint**

Run: `cd src/web-ui && npm run lint`
Expected: no new errors.

- [ ] **Step 4: Commit**

```bash
jj commit -m "feat(web-ui): Footer uses next-intl"
```

---

## Task 12: Locale switcher component

**Files:**
- Create: `src/web-ui/src/components/LocaleSwitcher.tsx`
- Modify: `src/web-ui/src/components/Navigation.tsx`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(web-ui): add locale switcher"
```

- [ ] **Step 2: Write `LocaleSwitcher.tsx`**

```tsx
"use client";

import { useLocale } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import { locales, localeLabels, type Locale } from "@/i18n/config";

export function LocaleSwitcher() {
  const locale = useLocale() as Locale;
  const pathname = usePathname();
  const router = useRouter();

  const other = locales.find((l) => l !== locale)!;

  return (
    <button
      type="button"
      onClick={() => router.replace(pathname, { locale: other })}
      className="text-sm text-slate-400 hover:text-white transition-colors"
      aria-label={`Switch to ${localeLabels[other]}`}
    >
      {localeLabels[other]}
    </button>
  );
}
```

- [ ] **Step 3: Mount in `Navigation.tsx`**

Import `LocaleSwitcher` and render it in the desktop nav (end of the flex row of links) and the mobile nav (end of the mobile menu list). Keep it visually consistent with surrounding nav items.

- [ ] **Step 4: Lint**

Run: `cd src/web-ui && npm run lint`
Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
jj commit -m "feat(web-ui): add locale switcher to Navigation"
```

---

## Task 13: `hreflang` alternates via metadata

**Files:**
- Modify: `src/web-ui/src/app/[locale]/layout.tsx`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(web-ui): emit hreflang alternates"
```

- [ ] **Step 2: Add `generateMetadata` to `[locale]/layout.tsx`**

Below the existing imports, add:

```tsx
import type { Metadata } from "next";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return {
    alternates: {
      canonical: locale === "is" ? "/" : `/${locale}`,
      languages: {
        is: "/",
        en: "/en",
        "x-default": "/",
      },
    },
  };
}
```

Note: Next.js's metadata merger means the root `layout.tsx` metadata (title, description, openGraph) remains in effect; this only adds alternates.

- [ ] **Step 3: Lint + typecheck**

Run: `cd src/web-ui && npm run lint`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
jj commit -m "feat(web-ui): emit hreflang alternates in per-locale metadata"
```

---

## Task 14: `/api/revalidate-i18n` route

**Files:**
- Create: `src/web-ui/src/app/api/revalidate-i18n/route.ts`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(web-ui): /api/revalidate-i18n route"
```

- [ ] **Step 2: Write the route**

```ts
import { NextResponse } from "next/server";
import { revalidateTag } from "next/cache";
import { locales } from "@/i18n/config";

export async function POST(request: Request) {
  const secret = process.env.WEB_UI_REVALIDATE_SECRET;
  if (!secret) {
    return NextResponse.json(
      { error: "WEB_UI_REVALIDATE_SECRET not configured" },
      { status: 500 },
    );
  }

  const provided = request.headers.get("x-revalidate-secret");
  if (provided !== secret) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  let body: { locale?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }

  const locale = body.locale;
  if (
    typeof locale !== "string" ||
    !(locales as readonly string[]).includes(locale)
  ) {
    return NextResponse.json({ error: "invalid locale" }, { status: 400 });
  }

  revalidateTag(`i18n:${locale}`);
  return NextResponse.json({ revalidated: true, locale });
}
```

- [ ] **Step 3: Verify the Django side sends the header the route expects**

Read `src/django-backend/apps/translations/services/revalidation.py` (or wherever the webhook helper lives — identify via `grep -rn "WEB_UI_REVALIDATE_SECRET" src/django-backend/`). Confirm the outgoing request sends the shared secret as the `X-Revalidate-Secret` HTTP header (case-insensitive). If it uses a different header name, update the Django helper to use `X-Revalidate-Secret` and regenerate the OpenAPI if any schema changed (`cd src/django-backend && make extract-openapi` then `cd src/web-ui && npm run generate-types`).

- [ ] **Step 4: Lint + typecheck**

Run: `cd src/web-ui && npm run lint`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
jj commit -m "feat(web-ui): /api/revalidate-i18n route (shared secret + tag revalidation)"
```

---

## Task 15: Django migration seeding `is` rows for chrome keys

**Files:**
- Create: `src/django-backend/apps/translations/migrations/0003_seed_phase2_ui_chrome.py`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(translations): seed is rows for Phase 2 chrome keys"
```

- [ ] **Step 2: Inspect current migration state**

Run: `ls src/django-backend/apps/translations/migrations/`
Note the highest-numbered migration. If it is not `0002_*`, rename the file created in this task accordingly (e.g. `0004_...`) so it sequences correctly.

- [ ] **Step 3: Write the migration**

```python
from django.db import migrations


# Mirror of the keys used by Navigation + Footer in the web-ui.
# Phase 3 replaces this hand-written seed with an auto-generated migration
# produced by `make translate-new-keys`.
IS_CHROME = {
    "nav.home": "Heim",
    "nav.projects": "Verkefni",
    "nav.competitions": "Keppnir",
    "nav.why": "Af hverju",
    "nav.about": "Um okkur",
    "nav.login": "Innskráning",
    "nav.register": "Nýskráning",
    "nav.submit": "Skila verkefni",
    "nav.myProjects": "Mín verkefni",
    "nav.myReviews": "Mínar umsagnir",
    "nav.profile": "Prófíll",
    "nav.logout": "Útskráning",
    "footer.about": "Um okkur",
    "footer.privacy": "Persónuvernd",
    "footer.discord": "Discord",
}


def seed(apps, schema_editor):
    Translation = apps.get_model("translations", "Translation")
    for key, text in IS_CHROME.items():
        Translation.objects.update_or_create(
            locale="is",
            key=key,
            defaults={
                "text": text,
                "source_hash": "",
                "is_machine_translated": True,
                "retired": False,
            },
        )


def unseed(apps, schema_editor):
    Translation = apps.get_model("translations", "Translation")
    Translation.objects.filter(locale="is", key__in=list(IS_CHROME)).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("translations", "0002_translationaudit"),  # adjust if latest differs
    ]
    operations = [migrations.RunPython(seed, unseed)]
```

Adjust the final key list to match the exact keys used in `en.json` at the end of Task 10 + Task 11 (they must be identical — these keys are what Icelandic users see).

- [ ] **Step 4: Apply + run tests**

Run:
```bash
cd src/django-backend
uv run python manage.py migrate
make test
```

Expected: migration applies cleanly; full test suite still passes (484+ tests).

- [ ] **Step 5: Commit**

```bash
jj commit -m "feat(translations): seed is rows for Phase 2 chrome keys"
```

---

## Task 16: Manual end-to-end browser check

**Files:**
- None (verification only)

- [ ] **Step 1: Start the backend (leave running)**

In terminal A:

```bash
cd src/django-backend
WEB_UI_REVALIDATE_URL=http://localhost:3000/api/revalidate-i18n \
WEB_UI_REVALIDATE_SECRET=dev-secret \
uv run python manage.py runserver 8001
```

- [ ] **Step 2: Start the web-ui (leave running)**

In terminal B:

```bash
cd src/web-ui
API_URL=http://localhost:8001 \
NEXT_PUBLIC_API_URL=http://localhost:8001 \
WEB_UI_REVALIDATE_SECRET=dev-secret \
npm run dev
```

Expected: server starts on port 3000.

- [ ] **Step 3: Verify Icelandic at `/`**

Browse http://localhost:3000/. Navigation shows `Heim`, `Verkefni`, `Keppnir`, etc. — the Icelandic values from the migration.

- [ ] **Step 4: Verify English at `/en`**

Browse http://localhost:3000/en. Navigation shows `Home`, `Projects`, `Competitions`, etc. — English values from `en.json`.

- [ ] **Step 5: Verify locale switcher**

From `/` click the switcher. URL becomes `/en`. Click it again; URL returns to `/`.

- [ ] **Step 6: Verify `hreflang`**

View page source at `/`. Confirm these tags are present:
```
<link rel="alternate" hrefLang="is" href="/" />
<link rel="alternate" hrefLang="en" href="/en" />
<link rel="alternate" hrefLang="x-default" href="/" />
```

- [ ] **Step 7: Verify live revalidation**

In a third terminal:

```bash
# Acquire a token as in Phase 1 smoke test (see docs/superpowers/verify.md).
TOKEN=... # from docs/superpowers/verify.md step 1

curl -s -X PATCH http://localhost:8001/api/i18n/is/nav.home \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"text":"HEIMHEIM"}' | jq .
```

Reload `http://localhost:3000/`. The nav label for "Home" reads `HEIMHEIM`.

Reset:
```bash
curl -s -X PATCH http://localhost:8001/api/i18n/is/nav.home \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Heim"}' | jq .
```

- [ ] **Step 8: Stop servers**

Ctrl-C in terminals A and B.

(No commit — verification only.)

---

## Task 17: Playwright smoke test

**Files:**
- Create: `src/web-ui/e2e/i18n.spec.ts`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "test(web-ui): Playwright smoke for bilingual rendering"
```

- [ ] **Step 2: Check Playwright config for baseURL**

Read `src/web-ui/playwright.config.ts`. Note `use.baseURL` and whether it starts the dev server automatically (`webServer`). If it does not start the backend, the test below assumes both servers are already running (document that expectation in a comment at the top of the spec).

- [ ] **Step 3: Write `e2e/i18n.spec.ts`**

```ts
import { test, expect } from "@playwright/test";

// Requires:
//   - Django backend on $API_URL (default http://localhost:8001) with
//     migration 0003_seed_phase2_ui_chrome applied.
//   - Web-ui on Playwright's baseURL.

test("renders Icelandic nav at /", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("link", { name: "Heim" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Verkefni" })).toBeVisible();
});

test("renders English nav at /en", async ({ page }) => {
  await page.goto("/en");
  await expect(page.getByRole("link", { name: "Home" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Projects" })).toBeVisible();
});

test("locale switcher toggles between is and en", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /English/ }).click();
  await expect(page).toHaveURL(/\/en/);
  await expect(page.getByRole("link", { name: "Home" })).toBeVisible();
  await page.getByRole("button", { name: /Íslenska/ }).click();
  await expect(page).toHaveURL(/^http:\/\/[^/]+\/$/);
  await expect(page.getByRole("link", { name: "Heim" })).toBeVisible();
});
```

- [ ] **Step 4: Run**

Run: `cd src/web-ui && npm run test:e2e -- i18n.spec.ts`
Expected: all three tests pass.

- [ ] **Step 5: Commit**

```bash
jj commit -m "test(web-ui): Playwright smoke for bilingual rendering"
```

---

## Task 18: Full CI gate

**Files:**
- None (verification only)

- [ ] **Step 1: Backend lint + tests**

Run:
```bash
cd src/django-backend
make lint
make test
```
Expected: both pass.

- [ ] **Step 2: Web-ui lint + typecheck**

Run:
```bash
cd src/web-ui
npm run lint
```
Expected: pass.

- [ ] **Step 3: Full CI**

Run: `cd /Users/alex/Work/codalens/nglspn/nglspn-w1 && make ci`
Expected: pass.

- [ ] **Step 4: Commit (only if CI prompted any formatting changes)**

```bash
jj new -m "chore: CI gate cleanup for Phase 2"
# apply any autoformat fixes
jj commit -m "chore: CI gate cleanup for Phase 2"
```

If nothing changed, skip.

---

## Done

At the end of Phase 2:
- `/` serves Icelandic Navigation + Footer from the Django catalog.
- `/en` serves English Navigation + Footer from `en.json`.
- Editing a translation via PATCH on the Django API flips the live text on `/` within seconds thanks to the `revalidateTag` webhook.
- `hreflang` alternates emitted; `<html lang>` reflects active locale.
- All other pages still render (using their existing hardcoded strings); Phase 4 will sweep those onto `t()`.

Next session: write Phase 3 plan (MT-assisted migration generator + developer authoring flow + lint rules).
