import type { components } from "../api-types";
import type { APIClient } from "./base";

export type NotificationSummary =
  components["schemas"]["NotificationSummaryResponse"];
export type NotificationGroup =
  components["schemas"]["NotificationGroupResponse"];
export type NotificationProject =
  components["schemas"]["NotificationProjectResponse"];

export class NotificationsClient {
  constructor(private client: APIClient) {}

  async getSummary(): Promise<NotificationSummary> {
    return this.client.request<NotificationSummary>(
      "/api/notifications/summary"
    );
  }

  async listGroups(limit?: number): Promise<NotificationGroup[]> {
    const qs = limit ? `?limit=${limit}` : "";
    return this.client.request<NotificationGroup[]>(
      `/api/notifications/groups${qs}`
    );
  }

  async markThreadRead(rootDiscussionId: string): Promise<{ marked: number }> {
    return this.client.request<{ marked: number }>(
      "/api/notifications/mark-thread-read",
      {
        method: "POST",
        body: JSON.stringify({ root_discussion_id: rootDiscussionId }),
      }
    );
  }

  async markThreadByComment(commentId: string): Promise<{ marked: number }> {
    return this.client.request<{ marked: number }>(
      "/api/notifications/mark-thread-read",
      {
        method: "POST",
        body: JSON.stringify({ comment_id: commentId }),
      }
    );
  }

  async markArticleThread(articleId: string): Promise<{ marked: number }> {
    return this.client.request<{ marked: number }>(
      "/api/notifications/mark-thread-read",
      {
        method: "POST",
        body: JSON.stringify({ article_id: articleId }),
      }
    );
  }

  async markAllRead(): Promise<{ marked: number }> {
    return this.client.request<{ marked: number }>(
      "/api/notifications/mark-all-read",
      { method: "POST" }
    );
  }
}
