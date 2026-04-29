## 1. Pre-flight: types and audit

- [x] 1.1 Confirm the regenerated TypeScript types (from the previous backend change) include `community_owned` on the create-project request, `creator` and `contributors[]` on project responses, and `is_system_user` on user summaries. If `is_system_user` is missing from `UserSummary`, add it to `api/schemas/users.py` (or wherever the summary serializer is defined), regenerate OpenAPI + types, and treat that as the smallest possible backend amendment as part of this change.
- [x] 1.2 Run a frontend audit: `grep -rn "project.owner\|\.owner\b" src/web-ui/src/` and list every site that needs updating. Capture the list as a checklist for §5.

## 2. Submit form: "I own this project" checkbox

- [x] 2.1 Locate the project create form (likely under `src/web-ui/src/app/submit/page.tsx` and/or a "create project" component on the my-projects page).
- [x] 2.2 Add a checkbox labelled "I own this project", checked by default. Add helper text immediately below: "Untick if you didn't make this project — it'll be added as a community submission" (final copy may be tweaked).
- [x] 2.3 Plumb the checkbox state into the create-project API call. When unticked, include `community_owned: true` in the request body; when ticked, omit `community_owned` (or send `false`).
- [ ] 2.4 Component test: ticked-by-default behaviour; toggling the checkbox flips the request payload's `community_owned`; unticked state is preserved across a validation-error re-render.

## 3. My-projects page: Suggested section

- [x] 3.1 Add an API client method for `GET /api/my-projects/suggestions` in `src/web-ui/src/lib/api/my-projects.ts` (or the equivalent file). Type the response identically to the existing my-projects list.
- [x] 3.2 In the my-projects page (or its `ProjectsList.tsx`), fetch both `/api/my-projects` and `/api/my-projects/suggestions` in parallel.
- [x] 3.3 Render two sections: "My Projects" (existing list, unchanged) and "Suggested" (new list). The Suggested section's heading AND list MUST be entirely hidden when the suggestions response is an empty array.
- [x] 3.4 Add a small "Suggested" badge to project cards rendered under either section when `project.contributors` includes any OWNER whose `user.is_system_user === true`. Reuse the existing card component; the badge is a small label, not a redesign.
- [ ] 3.5 Component test: empty suggestions hides both header and list; non-empty suggestions render correctly; user's own community submission appears in both sections with the badge.

## 4. Project detail title banner

- [x] 4.1 Update `ProjectTitleBanner.tsx` to compute `displayOwners = project.contributors.filter(c => c.role === "OWNER" && c.full_edit && !c.user.is_system_user)`.
- [x] 4.2 If `displayOwners.length === 0`, do not render any "by ..." line. The title, tagline, URL, and starred image all remain.
- [x] 4.3 If `displayOwners.length >= 1`, render the comma-joined list of names, linked to profile if applicable. Multi-owner rendering is a no-op today (max 1) but the code path supports the future group-owned case.
- [ ] 4.4 Component test: self-owned project renders the owner line; community-owned project does not; banner remains visually balanced in both cases (no broken DOM / no cascading shifts).

## 5. Project detail credit line

- [x] 5.1 Add a credit-line component (or section) below the tags / metadata area. Render "Suggested by {creator.name}" when the project's `creator.id` is not present in the `displayOwners` set; render "Created by {creator.name}" otherwise.
- [x] 5.2 Link the creator's name to their profile page if profile pages exist; otherwise render as plain text.
- [ ] 5.3 Component test: self-owned project shows "Created by ..."; community submission shows "Suggested by ..."; the line is below the tags / metadata, not in the banner.

## 6. Sweep `project.owner` references

- [x] 6.1 For each entry on the audit list from §1.2, replace `project.owner` with `project.creator` (for "who created this") or with a contributor-derived value (for "who can act on this"). Specifically:
  - `ProjectTitleBanner.tsx` — handled in §4.
  - `ProjectsList.tsx`, `ProjectDetail.tsx`, `EditProjectContent.tsx`, `submit/page.tsx`, `my-projects/page.tsx`, `onboarding/page.tsx`, `Navigation.tsx`, `auth-routing.ts`, `utils.ts`, `api/api.ts`, `api/index.ts` — replace each owner read with `creator` or contributors-derived as appropriate.
- [x] 6.2 Re-run the grep (`grep -rn "project.owner\|\.owner\b" src/web-ui/src/`); the only remaining matches should be type definitions or imports — none should be field reads against a project response.

## 7. Verification

- [x] 7.1 Run `npm run lint` from `src/web-ui/` and fix any new warnings.
- [x] 7.2 Run any existing component / unit tests; add the focused tests called out in §2.4, §3.5, §4.4, §5.3 if not already added inline.
- [ ] 7.3 Playwright (or manual) golden paths:
  - Submit a self-owned project; confirm it appears in "My Projects" without a "Suggested" badge; project detail shows "by {me}" and "Created by {me}".
  - Submit a community-owned project (untick the checkbox); confirm it appears in BOTH "My Projects" (with badge) AND "Suggested"; project detail omits the "by ..." line and shows "Suggested by {me}" below the tags.
  - As a different user, view both projects' detail pages and confirm rendering matches the same rules.
- [x] 7.4 Run `openspec validate community-suggestions-ui --strict` and confirm validation passes.
