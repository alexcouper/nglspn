# i18n groundwork: UI strings live in `src/i18n`

Issue #103. English only, no locale routing, no Icelandic yet. The point is that
components stop owning their copy, so that when Icelandic arrives (#2) it is a
translation job, not a rewrite.

## Decisions

- **Library: next-intl**, set up [without i18n routing](https://next-intl.dev/docs/getting-started/app-router/without-i18n-routing).
  `src/web-ui/src/i18n/request.ts` fixes the locale to `en` and loads the
  messages; `next.config.ts` wires it in; the root layout renders
  `NextIntlClientProvider` with no props, so client components inherit the same
  messages the server used.
- **One JSON file per area**, not one for the whole app:
  `src/web-ui/src/i18n/<area>/en.json`. `messages.ts` merges them into one
  object keyed by area, so the area name is the namespace:
  `useTranslations("auth.login")` reads `auth/en.json` → `login`.
- **Typed keys.** `next-intl.d.ts` registers the merged object with next-intl,
  so a misspelt or deleted key fails `tsc`.
- **Lint ratchet.** `eslint-rules/no-hardcoded-ui-strings.mjs` fails on text
  written into JSX. Files that have not been moved over yet are listed in
  `eslint-rules/i18n-pending.mjs` with the rule off; that list only shrinks.

The previous attempt (April 2026: translations app, inline editing, dynamic
loading) was removed for doing too much at once. This is deliberately the
minimum.

## Areas

| Area | Covers |
|------|--------|
| `common` | Navigation, footer, user menu, `actions` (Save, Cancel, …), `errors`, `states`, site metadata |
| `auth` | Login, register, verify email, onboarding steps |
| `projects` | Public listing, discover, project page, tiles, follow, tipoffs, tags |
| `my-projects` | Owner-side project editing, create, publish/delete dialogs |
| `articles` | Article authoring, editor dialogs, article cards and pages |
| `discussions` | Discussion lists, reply forms, inline discussions |
| `competitions` | Competition pages, entry and ranking dialogs, reviewer pages |
| `notifications` | Bell, feed, toasts for notifications |
| `feed` | `/latest` |
| `profile` | Own profile, settings, following, public user page |
| `images` | Image upload, cropper, role and alt-text dialogs |
| `guides` | Guide chrome (not the markdown content) |
| `about` | About, why, prizes, privacy |

Pick the area by what the user is doing, not by directory. A dialog under
`my-projects/[id]` that enters a competition is `competitions`.

## Conventions

- **Keys are nested per component, camelCase, named for meaning not text.**
  `register.errors.passwordTooShort`, not `register.passwordMustBe8Chars`.
  Renaming the English must not rename the key.
- **Generic words come from `common.actions`** (`cancel`, `save`, `saving`, …).
  Do not add a second `Cancel` to an area file. Anything with context ("Delete
  project") belongs to the area.
- **Interpolation and plurals are ICU**, inside the message:
  `"codeSubtitle": "We sent a 6-digit code to {email}"`,
  `"attemptsRemaining": "{count, plural, one {# attempt} other {# attempts}} remaining"`.
  Never concatenate fragments in JSX — word order differs between languages.
- **Inline markup uses `t.rich`** with the tag named in the message:
  `"privacyNotice": "By creating an account, you agree to our <link>Privacy Policy</link>."`
  and `t.rich("privacyNotice", { link: (chunks) => <Link …>{chunks}</Link> })`.
- **Client components:** `const t = useTranslations("area.component")`.
  **Server components:** `const t = await getTranslations("area.component")`;
  the component becomes `async`. Static `export const metadata` becomes
  `generateMetadata` when its strings move.
- **Strings decided outside JSX** (`setError(...)`, toast titles) still go
  through `t`; pass `t` into helpers rather than importing messages directly.
- **Brand name** `naglasúpan` is allow-listed in the rule and may stay inline.

## Tests

Components mount bare with `createRoot`, so `src/test/setup.ts` replaces
next-intl's hooks with translators over the real English messages. Tests keep
asserting on visible English text; nothing is wrapped. The shim covers
`useTranslations`, `useLocale`, `useFormatter` and their `next-intl/server`
counterparts.

`eslint-rules/no-hardcoded-ui-strings.test.mjs` runs the rule's fixtures and
checks that every `src/i18n/<area>/` has an `en.json` and is imported by
`messages.ts`, and that the pending list names only files that still exist.

## Moving a file over

1. Add the strings to the area's `en.json` under a key for the component.
2. Replace the JSX text and readable attributes with `t(...)`.
3. Delete the file's line from `eslint-rules/i18n-pending.mjs`.
4. `npx eslint <file>`, `npx tsc --noEmit`, and the file's vitest tests.

## Not done here, on purpose

- **Non-component strings:** `src/lib/api/errors.ts` (`describeApiError`'s
  three fixed messages), `VerifyCodeError.message` in `src/lib/api/auth.ts`,
  and anything else that builds a sentence outside a component. These need `t`
  threaded in or a key returned instead of a sentence; separate change.
- **`/is/guides`**: Icelandic guide content with Icelandic chrome. It is
  excluded from the rule outright, not pending. It gets folded in when locale
  routing exists.
- **Locale switching, Icelandic messages, inline editing.** See #103's scope.

## Cost

The next-intl runtime (ICU parser and formatter) adds about 12 kB gzipped to
the shared client chunk every route loads. `bundle-budgets.json` was raised for
the two routes that were already within that margin of their budget.
