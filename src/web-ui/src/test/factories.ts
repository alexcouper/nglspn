import type {
  ReviewCompetitionDetailResponse,
  ReviewProject,
  User,
} from "@/lib/api";

let tokenCounter = 0;

export function makeAccessToken(): string {
  tokenCounter += 1;
  return `access-token-${tokenCounter}`;
}

/** Signed in, as far as the browser can tell: an access token in localStorage. */
export function seedAccessToken(token: string = makeAccessToken()): string {
  localStorage.setItem("access_token", token);
  return token;
}

/**
 * An access token shaped like the backend's: a JWT whose payload names the
 * user. The signature is nonsense; the client never checks it.
 */
export function makeAccessTokenFor(userId: string): string {
  const encode = (value: unknown) =>
    btoa(JSON.stringify(value)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return `${encode({ alg: "HS256", typ: "JWT" })}.${encode({ user_id: userId, type: "access" })}.signature`;
}

/** A refresh token left behind by a build that kept it in localStorage. */
export function seedLegacyRefreshToken(): string {
  tokenCounter += 1;
  const token = `legacy-refresh-token-${tokenCounter}`;
  localStorage.setItem("refresh_token", token);
  return token;
}

let userCounter = 0;

export function makeUser(overrides: Partial<User> = {}): User {
  userCounter += 1;
  return {
    id: `user-${userCounter}`,
    email: `user${userCounter}@example.com`,
    first_name: "Test",
    last_name: `User ${userCounter}`,
    info: "",
    is_verified: true,
    is_system_user: false,
    avatar_url: null,
    created_at: "2026-01-01T00:00:00Z",
    groups: [],
    opt_in_to_external_promotions: true,
    discussion_email_frequency: "hourly",
    article_email_frequency: "hourly",
    pending_onboarding_steps: [],
    ...overrides,
  };
}

let reviewProjectCounter = 0;

export function makeReviewProject(
  overrides: Partial<ReviewProject> = {},
): ReviewProject {
  reviewProjectCounter += 1;
  return {
    id: `project-${reviewProjectCounter}`,
    slug: `project-${reviewProjectCounter}`,
    title: `Project ${reviewProjectCounter}`,
    tagline: "",
    description: "",
    website_url: "https://example.com",
    my_ranking: null,
    ...overrides,
  };
}

export function makeReviewProjects(count: number): ReviewProject[] {
  return Array.from({ length: count }, () => makeReviewProject());
}

export function makeReviewCompetitionDetail(
  overrides: Partial<ReviewCompetitionDetailResponse> = {},
): ReviewCompetitionDetailResponse {
  return {
    id: "competition-1",
    name: "Test Competition",
    start_date: "2025-01-01",
    submission_deadline: "2025-01-31",
    my_review_status: "in_progress",
    ranked_projects: [],
    pool_projects: [],
    ...overrides,
  };
}

/** A ready review state with the given ballot split, as the server returns it. */
export function makeReadyReviewState(
  ranked: ReviewProject[],
  pool: ReviewProject[],
  overrides: Partial<ReviewCompetitionDetailResponse> = {},
) {
  const data = makeReviewCompetitionDetail({
    ranked_projects: ranked.map((project, index) => ({
      ...project,
      my_ranking: index + 1,
    })),
    pool_projects: pool,
    ...overrides,
  });
  return {
    kind: "ready" as const,
    data,
    ranked: data.ranked_projects,
    pool: data.pool_projects,
  };
}
