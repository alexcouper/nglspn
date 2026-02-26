// Main API instance
export { api, API } from "./api";

// Base client
export { APIClient, API_BASE_URL, ApiRequestError } from "./base";

// Sub-clients
export { AuthClient } from "./auth";
export { CompetitionsClient } from "./competitions";
export { ProjectsClient } from "./projects";
export { MyProjectsClient } from "./my-projects";
export { MyReviewClient } from "./my-review";
export { UsersClient } from "./users";
export { TagsClient } from "./tags";

// Types - Auth
export type { User, TokenResponse, VerifyEmailResponse, ResendVerificationResponse } from "./auth";
export { VerifyCodeError } from "./auth";

// Types - Competitions
export type {
  Competition,
  CompetitionOverview,
  CompetitionOverviewListResponse,
  CompetitionSummary,
  CompetitionListResponse,
  CompetitionProject,
  Tag,
  ActiveOrRecentResponse,
} from "./competitions";

// Types - Projects
export type { Project, ProjectListResponse, ListProjectsParams } from "./projects";

// Types - My Projects
export type {
  ProjectCreate,
  ProjectImage,
  PresignedUploadResponse,
} from "./my-projects";

// Types - My Review
export type {
  ReviewCompetitionListResponse,
  ReviewCompetitionDetailResponse,
  ReviewCompetition,
  ReviewProject,
  ReviewProjectDetail,
  ReviewStatus,
} from "./my-review";

// Types - Users
export type { PublicUserProfile } from "./users";

// Types - Tags
export type { TagCategory, TagWithCategory, TagGrouped, TagSuggestRequest } from "./tags";
