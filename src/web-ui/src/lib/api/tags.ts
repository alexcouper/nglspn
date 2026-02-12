import type { components } from "../api-types";
import type { APIClient } from "./base";

export type TagCategory = components["schemas"]["TagCategoryResponse"];
export type TagWithCategory = components["schemas"]["TagWithCategoryResponse"];
export type TagGrouped = components["schemas"]["TagGroupedResponse"];
export type TagSuggestRequest = components["schemas"]["TagSuggestRequest"];

export class TagsClient {
  constructor(private client: APIClient) {}

  async listCategories(): Promise<TagCategory[]> {
    return this.client.request<TagCategory[]>("/api/tags/categories");
  }

  async listGrouped(options?: { withProjects?: boolean }): Promise<TagGrouped[]> {
    const params = new URLSearchParams();
    if (options?.withProjects) {
      params.set("with_projects", "true");
    }
    const query = params.toString();
    const endpoint = query ? `/api/tags/grouped?${query}` : "/api/tags/grouped";
    return this.client.request<TagGrouped[]>(endpoint);
  }

  async suggest(data: TagSuggestRequest): Promise<TagWithCategory> {
    return this.client.request<TagWithCategory>("/api/tags/suggest", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }
}
