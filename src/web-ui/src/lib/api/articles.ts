import type { components } from "../api-types";
import type { APIClient } from "./base";

export type Article = components["schemas"]["ArticleOut"];
export type ArticleListItem = components["schemas"]["ArticleListItem"];
export type ArticleCreate = components["schemas"]["ArticleCreate"];
export type ArticleUpdate = components["schemas"]["ArticleUpdate"];
export type ArticlePublish = components["schemas"]["ArticlePublish"];
export type FeedEventSuggestion =
  components["schemas"]["FeedEventSuggestion"];
// How the article's listing image was decided. Generated from
// ListingImageMode in apps/articles/models.py.
export type ListingImageMode = components["schemas"]["ListingImageMode"];
export type ProjectImage = components["schemas"]["ProjectImageResponse"];
export type PresignedUploadResponse =
  components["schemas"]["PresignedUploadResponse"];

export class ArticlesClient {
  constructor(private client: APIClient) {}

  async list(projectSlug: string): Promise<ArticleListItem[]> {
    return this.client.request<ArticleListItem[]>(
      `/api/projects/${projectSlug}/articles`
    );
  }

  async get(projectSlug: string, articleId: string): Promise<Article> {
    return this.client.request<Article>(
      `/api/projects/${projectSlug}/articles/${articleId}`
    );
  }

  async getBySlug(
    projectSlug: string,
    articleSlug: string
  ): Promise<Article> {
    return this.client.request<Article>(
      `/api/projects/${projectSlug}/articles/by-slug/${articleSlug}`
    );
  }

  async create(projectSlug: string, body: ArticleCreate): Promise<Article> {
    return this.client.request<Article>(
      `/api/projects/${projectSlug}/articles`,
      { method: "POST", body: JSON.stringify(body) }
    );
  }

  async update(
    projectSlug: string,
    articleId: string,
    body: ArticleUpdate
  ): Promise<Article> {
    return this.client.request<Article>(
      `/api/projects/${projectSlug}/articles/${articleId}`,
      { method: "PATCH", body: JSON.stringify(body) }
    );
  }

  async publish(
    projectSlug: string,
    articleId: string,
    body: ArticlePublish = {}
  ): Promise<Article> {
    return this.client.request<Article>(
      `/api/projects/${projectSlug}/articles/${articleId}/publish`,
      { method: "POST", body: JSON.stringify(body) }
    );
  }

  // Events this article could be the write-up of, best guess first. Empty is
  // the normal case — most articles are about nothing but themselves.
  async feedEventSuggestions(
    projectSlug: string,
    articleId: string
  ): Promise<FeedEventSuggestion[]> {
    return this.client.request<FeedEventSuggestion[]>(
      `/api/projects/${projectSlug}/articles/${articleId}/feed-event-suggestions`
    );
  }

  async delete(projectSlug: string, articleId: string): Promise<void> {
    await this.client.request<void>(
      `/api/projects/${projectSlug}/articles/${articleId}`,
      { method: "DELETE" }
    );
  }

  // Images are addressed under the article that owns them. The rows are the
  // same `ProjectImage` the project gallery uses — same storage, same variants
  // — but an article upload never enters that gallery, so it is never reached
  // through the my-projects image endpoints.
  async getImageUploadUrl(
    projectSlug: string,
    articleId: string,
    filename: string,
    contentType: string,
    fileSize: number
  ): Promise<PresignedUploadResponse> {
    return this.client.request<PresignedUploadResponse>(
      `/api/projects/${projectSlug}/articles/${articleId}/images/upload-url`,
      {
        method: "POST",
        body: JSON.stringify({
          filename,
          content_type: contentType,
          file_size: fileSize,
        }),
      }
    );
  }

  async completeImageUpload(
    projectSlug: string,
    articleId: string,
    imageId: string,
    // Measured client-side so the listing-image wizard knows the shape it has
    // to crop straight away, rather than waiting for the variant job to
    // backfill it.
    dimensions: { width: number; height: number } | null = null
  ): Promise<ProjectImage> {
    return this.client.request<ProjectImage>(
      `/api/projects/${projectSlug}/articles/${articleId}/images/${imageId}/complete`,
      {
        method: "POST",
        body: JSON.stringify(dimensions ?? {}),
      }
    );
  }

  async deleteImage(
    projectSlug: string,
    articleId: string,
    imageId: string
  ): Promise<void> {
    await this.client.request<void>(
      `/api/projects/${projectSlug}/articles/${articleId}/images/${imageId}`,
      { method: "DELETE" }
    );
  }
}
