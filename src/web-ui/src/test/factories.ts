import type {
  ReviewCompetitionDetailResponse,
  ReviewProject,
} from "@/lib/api";

export interface TokenPair {
  access: string;
  refresh: string;
}

let tokenCounter = 0;

export function makeTokenPair(overrides: Partial<TokenPair> = {}): TokenPair {
  tokenCounter += 1;
  return {
    access: `access-token-${tokenCounter}`,
    refresh: `refresh-token-${tokenCounter}`,
    ...overrides,
  };
}

export function seedTokens(tokens: TokenPair) {
  localStorage.setItem("access_token", tokens.access);
  localStorage.setItem("refresh_token", tokens.refresh);
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
    main_image_url: null,
    main_image_variants: [],
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
