import type { components } from "../api-types";
import type { APIClient } from "./base";

export type AdminProjectListResponse = components["schemas"]["AdminProjectListResponse"];
export type AdminProjectListItem = components["schemas"]["AdminProjectListItem"];
export type ProjectImagesGroupedResponse = components["schemas"]["ProjectImagesGroupedResponse"];

export class AdminClient {
  constructor(private client: APIClient) {}

  async listProjects(
    statusFilter?: string
  ): Promise<AdminProjectListResponse> {
    const params = statusFilter ? `?status_filter=${statusFilter}` : "";
    return this.client.request<AdminProjectListResponse>(
      `/api/admin/projects${params}`
    );
  }

  async getProjectImages(
    projectId: string
  ): Promise<ProjectImagesGroupedResponse> {
    return this.client.request<ProjectImagesGroupedResponse>(
      `/api/admin/projects/${projectId}`
    );
  }
}
