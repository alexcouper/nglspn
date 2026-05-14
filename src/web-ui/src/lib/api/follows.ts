import type { components } from "../api-types";
import type { APIClient } from "./base";

export type FollowState = components["schemas"]["FollowStateResponse"];

export class FollowsClient {
  constructor(private client: APIClient) {}

  async follow(slug: string): Promise<FollowState> {
    return this.client.request<FollowState>(
      `/api/projects/${slug}/follow`,
      { method: "POST" }
    );
  }

  async unfollow(slug: string): Promise<void> {
    await this.client.request<void>(
      `/api/projects/${slug}/follow`,
      { method: "DELETE" }
    );
  }
}
