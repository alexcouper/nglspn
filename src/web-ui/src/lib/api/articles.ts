import type { components } from "../api-types";
import type { APIClient } from "./base";

export type Article = components["schemas"]["ArticleOut"];
export type ArticleListItem = components["schemas"]["ArticleListItem"];
export type ArticleCreate = components["schemas"]["ArticleCreate"];
export type OwnArticleCreate = components["schemas"]["OwnArticleCreate"];
export type OwnArticle = components["schemas"]["OwnArticleResponse"];
export type ArticleUpdate = components["schemas"]["ArticleUpdate"];
export type ArticlePublish = components["schemas"]["ArticlePublish"];
// How the article's listing image was decided. Generated from
// ListingImageMode in apps/articles/models.py.
export type ListingImageMode = components["schemas"]["ListingImageMode"];
export type Image = components["schemas"]["ImageResponse"];
export type PresignedUploadResponse =
  components["schemas"]["PresignedUploadResponse"];

// Creation and reads by slug live under the article's container — a project,
// or the author. Everything addressed by article id lives at /api/articles/{id}
// and needs no container: the backend derives who may edit from the article.
export class ArticlesClient {
  constructor(private client: APIClient) {}

  async list(projectSlug: string): Promise<ArticleListItem[]> {
    return this.client.request<ArticleListItem[]>(
      `/api/projects/${projectSlug}/articles`
    );
  }

  // The editor's read: the article as its author or a contributor sees it,
  // whatever its state. Readers use the by-slug calls.
  async get(articleId: string): Promise<Article> {
    return this.client.request<Article>(`/api/articles/${articleId}`);
  }

  async getBySlug(
    projectSlug: string,
    articleSlug: string
  ): Promise<Article> {
    return this.client.request<Article>(
      `/api/projects/${projectSlug}/articles/by-slug/${articleSlug}`
    );
  }

  async getBySlugForUser(userId: string, articleSlug: string): Promise<Article> {
    return this.client.request<Article>(
      `/api/users/${userId}/articles/by-slug/${articleSlug}`
    );
  }

  async create(projectSlug: string, body: ArticleCreate): Promise<Article> {
    return this.client.request<Article>(
      `/api/projects/${projectSlug}/articles`,
      { method: "POST", body: JSON.stringify(body) }
    );
  }

  // A draft under the caller's own name: no project, and no channel to choose.
  async createOwn(
    body: OwnArticleCreate = { title: "", body: "" }
  ): Promise<Article> {
    return this.client.request<Article>("/api/auth/me/articles", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  // Everything the caller wrote, of both kinds and in every state — the
  // owner's profile list.
  async listOwn(): Promise<OwnArticle[]> {
    return this.client.request<OwnArticle[]>("/api/auth/me/articles");
  }

  async update(articleId: string, body: ArticleUpdate): Promise<Article> {
    return this.client.request<Article>(`/api/articles/${articleId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  async publish(
    articleId: string,
    body: ArticlePublish = {}
  ): Promise<Article> {
    return this.client.request<Article>(`/api/articles/${articleId}/publish`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  async delete(articleId: string): Promise<void> {
    await this.client.request<void>(`/api/articles/${articleId}`, {
      method: "DELETE",
    });
  }

  // Images are addressed under the article that owns them. The rows are the
  // same `Image` the project gallery uses — same storage, same variants
  // — but an article upload never enters that gallery, so it is never reached
  // through the my-projects image endpoints.
  async getImageUploadUrl(
    articleId: string,
    filename: string,
    contentType: string,
    fileSize: number
  ): Promise<PresignedUploadResponse> {
    return this.client.request<PresignedUploadResponse>(
      `/api/articles/${articleId}/images/upload-url`,
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
    articleId: string,
    imageId: string,
    // Measured client-side so the listing-image wizard knows the shape it has
    // to crop straight away, rather than waiting for the variant job to
    // backfill it.
    dimensions: { width: number; height: number } | null = null
  ): Promise<Image> {
    return this.client.request<Image>(
      `/api/articles/${articleId}/images/${imageId}/complete`,
      {
        method: "POST",
        body: JSON.stringify(dimensions ?? {}),
      }
    );
  }

  async deleteImage(articleId: string, imageId: string): Promise<void> {
    await this.client.request<void>(
      `/api/articles/${articleId}/images/${imageId}`,
      { method: "DELETE" }
    );
  }
}
