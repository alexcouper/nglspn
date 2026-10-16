# Proposal: user profile page

Design: [User Profile Page canvas](https://claude.ai/artifact/EtycAMJgbaSXFN7vuFHALR)
(three artboards: public profile on desktop, edit profile, public profile on a
phone).

## Why

Every project page and article byline links to `/users/{id}`, and what it lands
on is a name and a block of markdown in a card. Nothing tells a visitor what the
person has actually done here: which projects they own or tipped off, what they
have written. The link is a dead end, so people are not discoverable and there
is no reason to fill in a profile.

The owner's side is no better. `/profile` is one page that mixes the public
fields (name, about) with private account settings (email cadence, promotions
opt-in) behind an Edit/Preview toggle, and there is no avatar anywhere in the
product, so bylines, contributor lists and the nav all show text where a face
should be.

## What Changes

- **Public profile page** at `/users/{id}` gains an avatar, a "joined" line,
  the About markdown, the person's approved projects with their role on each,
  and the articles they have published. Own profile shows an **Edit profile**
  button.
- **Avatar.** A new per-user image: uploaded from the edit page through the same
  presigned-PUT flow as project and article images, cropped to a square in the
  browser before upload, replaceable and removable. Falls back to initials in
  the accent tint wherever it is shown. Exposed as `avatar_url` on the user
  schemas so bylines and contributor lists can pick it up later.
- **Two new read endpoints**, `GET /api/users/{id}/projects` and
  `GET /api/users/{id}/articles`, returning only what the public can already see
  elsewhere: approved projects, globally visible articles on approved projects.
- **Three new write endpoints** on the current user for the avatar: reserve an
  upload, complete it, delete it.
- **`/profile` becomes the edit page only**: avatar, first name, last name,
  About with a Write/Preview switch. Save returns to the public page; Cancel
  discards. The Edit/Preview toggle and the inline `ReadOnlyProfile` go.
- **Account settings move** to `/profile/settings` (promotions opt-in, discussion
  and article email cadence), linked from the edit page and the user menu.
- **`GET /api/users/{id}` returns 404 for system users and inactive accounts.**
  Both are already hidden from bylines and credits in the UI; the endpoint
  catches up. Not marked BREAKING: no client renders a profile for either
  today.
- `PublicUserProfile` gains `avatar_url` and `created_at`. Additive; the
  generated TypeScript types must be regenerated (see Impact).

Out of scope, deliberately: per-item show/hide controls on the project and
article lists (both are derived from contributorship and authorship and stay
that way), avatars in bylines and contributor lists beyond exposing the field,
server-side image processing for avatars, and any change to onboarding.

## Capabilities

### New Capabilities

- `user-profile-page`: the public profile route and the two list endpoints
  behind it; the edit page; the settings page split; who can see whose profile.
- `user-avatar`: the avatar model and lifecycle (reserve, upload, complete,
  replace, remove, orphan sweep), its exposure on the user schemas, and the
  initials fallback.

### Modified Capabilities

None. `mandatory-profile-names` still holds unchanged on the edit page: the
"at least one name" rule is kept as written. No existing spec covers
`GET /api/users/{id}`, the orphan sweep, or the `/profile` page layout.

## Impact

**Backend** (`src/django-backend/`)

- `apps/users/models.py`: new `UserAvatar` model and `User.avatar` FK, with a
  migration in the same change.
- `api/schemas/user.py`: `avatar_url`, `created_at` on `PublicUserProfile`;
  `avatar_url` on `UserResponse`; new list-item schemas for a user's projects
  and articles; avatar upload request/response reuse the project image shapes.
- `api/routers/users.py`: the two list endpoints, the 404 rule.
- `api/routers/auth.py`: three avatar endpoints under `/me/avatar`.
- `services/users/`: query methods for a user's public projects and articles;
  handler methods for the avatar lifecycle.
- `services/images/django_impl/handler.py`: the orphan sweep also reaps
  abandoned avatar reservations, and replaced or removed avatars leave an
  `OrphanedStorageObject` tombstone the existing drain picks up.
- `services/storage.py`: an upload-key generator for the `avatars/` prefix.
- **OpenAPI**: `make extract-openapi` after the schema changes and commit
  `src/web-ui/backend-openapi.json`; `make extra-tests` fails otherwise.

**Web UI** (`src/web-ui/`)

- `src/app/users/[id]/page.tsx` rebuilt to the design; `ReadOnlyProfile.tsx`
  removed.
- `src/app/profile/page.tsx` becomes the edit page; `Settings.tsx` moves to
  `src/app/profile/settings/page.tsx`; `UserMenu.tsx` gains a Settings entry.
- New `Avatar` component (image or initials) used on the profile pages and the
  nav's account button.
- `src/lib/api/users.ts` and `auth.ts` gain the new calls.
- Reuses `ProjectTile`, `ArticleCard`, `ImageCropper` and the presigned upload
  helpers as they are.

**Storage.** A new `avatars/{user_id}/…` key prefix in the same bucket. No
Terraform change: the bucket policy is prefix-agnostic.

**No change** to the login rate limit, the 10-image project cap, notifications,
or onboarding.
