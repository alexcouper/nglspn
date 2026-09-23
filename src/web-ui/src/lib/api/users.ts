import type { components } from "../api-types";
import type { APIClient } from "./base";

export type PublicUserProfile = components["schemas"]["PublicUserProfile"];
export type UserProject = components["schemas"]["UserProjectResponse"];
export type UserArticle = components["schemas"]["UserArticleResponse"];

export class UsersClient {
  constructor(private client: APIClient) {}

  async getPublicProfile(userId: string): Promise<PublicUserProfile> {
    return this.client.request<PublicUserProfile>(`/api/users/${userId}`);
  }

  // Approved projects the user contributes to, owners first. What a visitor
  // may see — the owner's drafts live on My Projects, not here.
  async listProjects(userId: string): Promise<UserProject[]> {
    return this.client.request<UserProject[]>(`/api/users/${userId}/projects`);
  }

  // Globally visible articles the user wrote on approved projects, newest
  // first.
  async listArticles(userId: string): Promise<UserArticle[]> {
    return this.client.request<UserArticle[]>(`/api/users/${userId}/articles`);
  }
}
