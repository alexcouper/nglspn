import { AdminClient } from "./admin";
import { APIClient } from "./base";
import { AuthClient } from "./auth";
import { CompetitionsClient } from "./competitions";
import { DiscussionsClient } from "./discussions";
import { ImagesClient } from "./images";
import { ProjectsClient } from "./projects";
import { MyProjectsClient } from "./my-projects";
import { MyReviewClient } from "./my-review";
import { UsersClient } from "./users";
import { TagsClient } from "./tags";

export class API {
  private client: APIClient;

  readonly admin: AdminClient;
  readonly auth: AuthClient;
  readonly competitions: CompetitionsClient;
  readonly discussions: DiscussionsClient;
  readonly images: ImagesClient;
  readonly projects: ProjectsClient;
  readonly myProjects: MyProjectsClient;
  readonly myReview: MyReviewClient;
  readonly users: UsersClient;
  readonly tags: TagsClient;

  constructor() {
    this.client = new APIClient();
    this.admin = new AdminClient(this.client);
    this.auth = new AuthClient(this.client);
    this.competitions = new CompetitionsClient(this.client);
    this.discussions = new DiscussionsClient(this.client);
    this.images = new ImagesClient(this.client);
    this.projects = new ProjectsClient(this.client);
    this.myProjects = new MyProjectsClient(this.client);
    this.myReview = new MyReviewClient(this.client);
    this.users = new UsersClient(this.client);
    this.tags = new TagsClient(this.client);
  }

  isAuthenticated(): boolean {
    return this.client.isAuthenticated();
  }

  clearTokens(): void {
    this.client.clearTokens();
  }
}

export const api = new API();
