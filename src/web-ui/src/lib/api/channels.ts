import type { components } from "../api-types";
import type { APIClient } from "./base";

export type Channel = components["schemas"]["ChannelResponse"];
export type ChannelCreate = components["schemas"]["ChannelCreate"];
export type ChannelRename = components["schemas"]["ChannelRename"];
export type ChannelReassign = components["schemas"]["ChannelReassign"];
export type ChannelConflictResponse =
  components["schemas"]["ChannelConflictResponse"];
export type ChannelReassignResponse =
  components["schemas"]["ChannelReassignResponse"];

export class ChannelsClient {
  constructor(private client: APIClient) {}

  async list(projectSlug: string): Promise<Channel[]> {
    return this.client.request<Channel[]>(
      `/api/projects/${projectSlug}/channels`
    );
  }

  async create(projectSlug: string, body: ChannelCreate): Promise<Channel> {
    return this.client.request<Channel>(
      `/api/projects/${projectSlug}/channels`,
      { method: "POST", body: JSON.stringify(body) }
    );
  }

  async rename(
    projectSlug: string,
    channelId: string,
    body: ChannelRename
  ): Promise<Channel> {
    return this.client.request<Channel>(
      `/api/projects/${projectSlug}/channels/${channelId}`,
      { method: "PATCH", body: JSON.stringify(body) }
    );
  }

  async delete(projectSlug: string, channelId: string): Promise<void> {
    await this.client.request<void>(
      `/api/projects/${projectSlug}/channels/${channelId}`,
      { method: "DELETE" }
    );
  }

  async reassign(
    projectSlug: string,
    channelId: string,
    body: ChannelReassign
  ): Promise<ChannelReassignResponse> {
    return this.client.request<ChannelReassignResponse>(
      `/api/projects/${projectSlug}/channels/${channelId}/reassign`,
      { method: "POST", body: JSON.stringify(body) }
    );
  }
}
