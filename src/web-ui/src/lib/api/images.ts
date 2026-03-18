import type { components } from "../api-types";
import type { APIClient } from "./base";

export type GenerateImageRequest = components["schemas"]["GenerateImageRequest"];
export type GenerateImageResponse = components["schemas"]["GenerateImageResponse"];
export type GenerationStatusResponse = components["schemas"]["GenerationStatusResponse"];
export type ProposedImageResponse = components["schemas"]["ProposedImageResponse"];
export type ProjectImagesGroupedResponse = components["schemas"]["ProjectImagesGroupedResponse"];
export type PurposeImageSlot = components["schemas"]["PurposeImageSlot"];

export class ImagesClient {
  constructor(private client: APIClient) {}

  async generate(body: GenerateImageRequest): Promise<GenerateImageResponse> {
    return this.client.request<GenerateImageResponse>("/api/images/generate", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  async getGenerationStatus(requestId: string): Promise<GenerationStatusResponse> {
    return this.client.request<GenerationStatusResponse>(
      `/api/images/generate/${requestId}`
    );
  }

  async acceptImage(imageId: string): Promise<ProposedImageResponse> {
    return this.client.request<ProposedImageResponse>(
      `/api/images/${imageId}/accept`,
      { method: "POST" }
    );
  }

  async rejectImage(imageId: string): Promise<void> {
    await this.client.request(`/api/images/${imageId}/reject`, {
      method: "POST",
    });
  }

  async getProjectImages(projectId: string): Promise<ProjectImagesGroupedResponse> {
    return this.client.request<ProjectImagesGroupedResponse>(
      `/api/images/project/${projectId}`
    );
  }
}
