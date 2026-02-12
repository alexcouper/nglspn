import type { components } from "../api-types";
import type { APIClient } from "./base";

export type PublicUserProfile = components["schemas"]["PublicUserProfile"];

export class UsersClient {
  constructor(private client: APIClient) {}

  async getPublicProfile(userId: string): Promise<PublicUserProfile> {
    return this.client.request<PublicUserProfile>(`/api/users/${userId}`);
  }
}
