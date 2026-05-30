import type { components } from "../api-types";
import type { APIClient } from "./base";

export type FollowState = components["schemas"]["FollowStateResponse"];
export type ChannelFollowState =
  components["schemas"]["ChannelFollowStateResponse"];
export type FollowWithPreferences = components["schemas"]["FollowResponse"];

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

  async listFollows(): Promise<FollowWithPreferences[]> {
    return this.client.request<FollowWithPreferences[]>("/api/follows");
  }

  async getFollowPreferences(
    slug: string
  ): Promise<FollowWithPreferences> {
    return this.client.request<FollowWithPreferences>(
      `/api/projects/${slug}/follow/preferences`
    );
  }

  async followChannel(
    slug: string,
    channelId: string
  ): Promise<ChannelFollowState> {
    return this.client.request<ChannelFollowState>(
      `/api/projects/${slug}/follow/channels/${channelId}`,
      { method: "POST" }
    );
  }

  async unfollowChannel(slug: string, channelId: string): Promise<void> {
    await this.client.request<void>(
      `/api/projects/${slug}/follow/channels/${channelId}`,
      { method: "DELETE" }
    );
  }
}
