import type { components } from "../api-types";
import type { APIClient } from "./base";
import type { Project } from "./projects";

export type { Project };
export type ProjectCreate = components["schemas"]["ProjectCreate"];
export type ProjectImage = components["schemas"]["ProjectImageResponse"];
export type PresignedUploadResponse =
  components["schemas"]["PresignedUploadResponse"];

export class MyProjectsClient {
  constructor(private client: APIClient) {}

  async create(data: ProjectCreate): Promise<Project> {
    return this.client.request<Project>("/api/my/projects", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async list(): Promise<Project[]> {
    return this.client.request<Project[]>("/api/my/projects");
  }

  async listTipOffs(): Promise<Project[]> {
    return this.client.request<Project[]>("/api/my/projects/tip-offs");
  }

  async get(id: string): Promise<Project> {
    return this.client.request<Project>(`/api/my/projects/${id}`);
  }

  async update(
    id: string,
    data: Partial<ProjectCreate>
  ): Promise<Project> {
    return this.client.request<Project>(`/api/my/projects/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async delete(id: string): Promise<void> {
    return this.client.request<void>(`/api/my/projects/${id}`, {
      method: "DELETE",
    });
  }

  async publish(id: string): Promise<Project> {
    return this.client.request<Project>(`/api/my/projects/${id}/publish`, {
      method: "POST",
    });
  }

  async getImageUploadUrl(
    projectId: string,
    filename: string,
    contentType: string,
    fileSize: number,
    isIcon: boolean = false,
    source: "project" | "article" = "project"
  ): Promise<PresignedUploadResponse> {
    return this.client.request<PresignedUploadResponse>(
      `/api/my/projects/${projectId}/images/upload-url`,
      {
        method: "POST",
        body: JSON.stringify({
          filename,
          content_type: contentType,
          file_size: fileSize,
          is_icon: isIcon,
          source,
        }),
      }
    );
  }

  async completeImageUpload(
    projectId: string,
    imageId: string,
    // Measured client-side. Without these the row's dimensions stay null until
    // the async variant job backfills them, and anything that needs to know the
    // image's shape straight away — the hero crop dialog — has nothing to work
    // with.
    dimensions: { width: number; height: number } | null = null
  ): Promise<ProjectImage> {
    return this.client.request<ProjectImage>(
      `/api/my/projects/${projectId}/images/${imageId}/complete`,
      {
        method: "POST",
        body: JSON.stringify(dimensions ?? {}),
      }
    );
  }

  async deleteImage(projectId: string, imageId: string): Promise<void> {
    return this.client.request<void>(
      `/api/my/projects/${projectId}/images/${imageId}`,
      { method: "DELETE" }
    );
  }

  async updateImageRoles(
    projectId: string,
    imageId: string,
    roles: { is_main?: boolean; is_hero?: boolean; is_usage?: boolean }
  ): Promise<ProjectImage> {
    return this.client.request<ProjectImage>(
      `/api/my/projects/${projectId}/images/${imageId}/roles`,
      {
        method: "POST",
        body: JSON.stringify(roles),
      }
    );
  }
}
