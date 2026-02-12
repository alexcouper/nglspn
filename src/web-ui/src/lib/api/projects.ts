import type { components } from "../api-types";
import type { APIClient } from "./base";

export type Project = components["schemas"]["ProjectResponse"];
export type ProjectListResponse = components["schemas"]["ProjectListResponse"];

export interface ListProjectsParams {
  tags?: string[];
  tech_stack?: string[];
  sort_by?: string;
  sort_order?: "asc" | "desc";
  search?: string;
  page?: number;
  per_page?: number;
}

export class ProjectsClient {
  constructor(private client: APIClient) {}

  async list(params: ListProjectsParams = {}): Promise<ProjectListResponse> {
    const searchParams = new URLSearchParams();

    if (params.tags) {
      params.tags.forEach((tag) => searchParams.append("tags", tag));
    }
    if (params.tech_stack) {
      params.tech_stack.forEach((tech) =>
        searchParams.append("tech_stack", tech)
      );
    }
    if (params.sort_by) searchParams.set("sort_by", params.sort_by);
    if (params.sort_order) searchParams.set("sort_order", params.sort_order);
    if (params.search) searchParams.set("search", params.search);
    if (params.page) searchParams.set("page", params.page.toString());
    if (params.per_page) searchParams.set("per_page", params.per_page.toString());

    const query = searchParams.toString();
    const endpoint = query ? `/api/projects?${query}` : "/api/projects";

    return this.client.request<ProjectListResponse>(endpoint);
  }

  async get(projectId: string): Promise<Project> {
    return this.client.request<Project>(`/api/projects/${projectId}`);
  }

  async getFeatured(): Promise<Project[]> {
    return this.client.request<Project[]>("/api/projects/featured");
  }

  async getTrending(): Promise<Project[]> {
    return this.client.request<Project[]>("/api/projects/trending");
  }
}
