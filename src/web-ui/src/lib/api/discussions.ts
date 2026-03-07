import type { components } from "../api-types";
import type { APIClient } from "./base";

export type Discussion = components["schemas"]["DiscussionResponse"];
export type Reply = components["schemas"]["ReplyResponse"];
export type DiscussionAuthor = components["schemas"]["DiscussionAuthor"];

export class DiscussionsClient {
  constructor(private client: APIClient) {}

  async list(projectId: string): Promise<Discussion[]> {
    return this.client.request<Discussion[]>(
      `/api/projects/${projectId}/discussions`
    );
  }

  async create(projectId: string, body: string): Promise<Discussion> {
    return this.client.request<Discussion>(
      `/api/projects/${projectId}/discussions`,
      {
        method: "POST",
        body: JSON.stringify({ body }),
      }
    );
  }

  async reply(
    projectId: string,
    discussionId: string,
    body: string
  ): Promise<Reply> {
    return this.client.request<Reply>(
      `/api/projects/${projectId}/discussions/${discussionId}/replies`,
      {
        method: "POST",
        body: JSON.stringify({ body }),
      }
    );
  }

  async delete(projectId: string, discussionId: string): Promise<void> {
    await this.client.request<void>(
      `/api/projects/${projectId}/discussions/${discussionId}`,
      {
        method: "DELETE",
      }
    );
  }
}
