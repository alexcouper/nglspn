import type { components } from "../api-types";
import type { APIClient } from "./base";

export type FeedEntry = components["schemas"]["FeedEntryResponse"];
export type FeedPage = components["schemas"]["FeedPageResponse"];

// Mirrors apps/feed/models.py FeedEventKind. The API sends the kind and the
// refs; the wording lives here with the rest of the UI's copy.
export type FeedEventKind = FeedEntry["kind"];

export class FeedClient {
  constructor(private client: APIClient) {}

  async page(options: { before?: string; limit?: number } = {}): Promise<FeedPage> {
    const params = new URLSearchParams();
    if (options.before) params.set("before", options.before);
    if (options.limit) params.set("limit", String(options.limit));
    const query = params.toString();
    return this.client.request<FeedPage>(`/api/feed${query ? `?${query}` : ""}`);
  }
}
