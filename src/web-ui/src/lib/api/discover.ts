import type { components } from "../api-types";
import type { APIClient } from "./base";

export type DiscoverProject =
  components["schemas"]["DiscoverProjectResponse"];
export type CategoryItem = components["schemas"]["CategoryResponse"];
export type WinnerProject = components["schemas"]["WinnerProjectResponse"];

export class DiscoverClient {
  constructor(private client: APIClient) {}

  async categories(): Promise<CategoryItem[]> {
    return this.client.request<CategoryItem[]>("/api/projects/categories");
  }

  async featured(): Promise<DiscoverProject[]> {
    return this.client.request<DiscoverProject[]>("/api/projects/featured");
  }

  async newArrivals(): Promise<DiscoverProject[]> {
    return this.client.request<DiscoverProject[]>("/api/projects/new-arrivals");
  }

  async recentTipoffs(): Promise<DiscoverProject[]> {
    return this.client.request<DiscoverProject[]>(
      "/api/projects/recent-tipoffs"
    );
  }

  async winners(): Promise<WinnerProject[]> {
    return this.client.request<WinnerProject[]>("/api/projects/winners");
  }

  async mostDiscussed(): Promise<DiscoverProject[]> {
    return this.client.request<DiscoverProject[]>(
      "/api/projects/most-discussed"
    );
  }

  async byCategory(
    slug: string,
    sort: "newest" | "name" | "most-discussed" = "newest"
  ): Promise<DiscoverProject[]> {
    const params = new URLSearchParams({ sort });
    return this.client.request<DiscoverProject[]>(
      `/api/projects/by-category/${slug}?${params}`
    );
  }
}
