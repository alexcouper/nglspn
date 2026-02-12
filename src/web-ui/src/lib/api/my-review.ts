import type { components } from "../api-types";
import type { APIClient } from "./base";

export type ReviewCompetitionListResponse =
  components["schemas"]["ReviewCompetitionListResponse"];
export type ReviewCompetitionDetailResponse =
  components["schemas"]["ReviewCompetitionDetailResponse"];
export type ReviewCompetition = components["schemas"]["ReviewCompetitionResponse"];
export type ReviewProject = components["schemas"]["ReviewProjectResponse"];
export type ReviewProjectDetail =
  components["schemas"]["ReviewProjectDetailResponse"];
export type ReviewStatus = components["schemas"]["ReviewStatusEnum"];

export class MyReviewClient {
  constructor(private client: APIClient) {}

  async getCompetitions(): Promise<ReviewCompetitionListResponse> {
    return this.client.request<ReviewCompetitionListResponse>(
      "/api/my/reviews/competitions"
    );
  }

  async getCompetition(
    competitionId: string
  ): Promise<ReviewCompetitionDetailResponse> {
    return this.client.request<ReviewCompetitionDetailResponse>(
      `/api/my/reviews/competitions/${competitionId}`
    );
  }

  async getProject(projectId: string): Promise<ReviewProjectDetail> {
    return this.client.request<ReviewProjectDetail>(
      `/api/my/reviews/projects/${projectId}`
    );
  }

  async updateRankings(
    competitionId: string,
    projectIds: string[]
  ): Promise<ReviewCompetitionDetailResponse> {
    return this.client.request<ReviewCompetitionDetailResponse>(
      `/api/my/reviews/competitions/${competitionId}/rankings`,
      {
        method: "PUT",
        body: JSON.stringify({ project_ids: projectIds }),
      }
    );
  }

  async updateStatus(competitionId: string, status: ReviewStatus): Promise<void> {
    return this.client.request<void>(
      `/api/my/reviews/competitions/${competitionId}/status`,
      {
        method: "PUT",
        body: JSON.stringify({ status }),
      }
    );
  }
}
