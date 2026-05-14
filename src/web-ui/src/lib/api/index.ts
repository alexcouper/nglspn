// Main API instance
export { api, API } from "./api";

// Base client
export { APIClient, API_BASE_URL, ApiRequestError } from "./base";

// Sub-clients
export { AuthClient } from "./auth";
export { CompetitionsClient } from "./competitions";
export { DiscoverClient } from "./discover";
export { DiscussionsClient } from "./discussions";
export { FollowsClient } from "./follows";
export { ProjectsClient } from "./projects";
export { MyProjectsClient } from "./my-projects";
export { MyReviewClient } from "./my-review";
export { NotificationsClient } from "./notifications";
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
  CompetitionHighlightsResponse,
} from "./competitions";

// Types - Discussions
export type { Discussion, Reply, DiscussionAuthor } from "./discussions";

// Types - Follows
export type { FollowState } from "./follows";

// Types - Discover
export type { DiscoverProject, CategoryItem, WinnerProject } from "./discover";

// Types - Projects
export type { Project, ProjectListItem, ProjectListResponse, ListProjectsParams } from "./projects";

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

// Types - Notifications
export type {
  NotificationGroup,
  NotificationProject,
  NotificationSummary,
} from "./notifications";
