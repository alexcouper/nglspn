import type { components } from "../api-types";
import type { APIClient } from "./base";

export type PublicUserProfile = components["schemas"]["PublicUserProfile"];
// The profile page's own response: the public profile plus `is_followed` for
// the viewer. Never embedded anywhere else.
export type UserProfile = components["schemas"]["UserProfileResponse"];
export type UserProject = components["schemas"]["UserProjectResponse"];
export type UserArticle = components["schemas"]["UserArticleResponse"];

export class UsersClient {
  constructor(private client: APIClient) {}

  async getPublicProfile(userId: string): Promise<UserProfile> {
    return this.client.request<UserProfile>(`/api/users/${userId}`);
  }

  // Approved projects the user contributes to, owners first. What a visitor
  // may see — the owner's drafts live on My Projects, not here.
  async listProjects(userId: string): Promise<UserProject[]> {
    return this.client.request<UserProject[]>(`/api/users/${userId}/projects`);
  }

  // Globally visible articles the user wrote, newest first: under their own
  // name (`project` null) and on approved projects.
  async listArticles(userId: string): Promise<UserArticle[]> {
    return this.client.request<UserArticle[]>(`/api/users/${userId}/articles`);
  }
}
