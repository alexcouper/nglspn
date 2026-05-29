import type { components } from "../api-types";
import type { APIClient } from "./base";

export type Article = components["schemas"]["ArticleOut"];
export type ArticleListItem = components["schemas"]["ArticleListItem"];
export type ArticleCreate = components["schemas"]["ArticleCreate"];
export type ArticleUpdate = components["schemas"]["ArticleUpdate"];
export type ArticlePublish = components["schemas"]["ArticlePublish"];

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

  async delete(projectSlug: string, articleId: string): Promise<void> {
    await this.client.request<void>(
      `/api/projects/${projectSlug}/articles/${articleId}`,
      { method: "DELETE" }
    );
  }
}
