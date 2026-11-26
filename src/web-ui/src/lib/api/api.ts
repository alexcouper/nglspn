import { APIClient } from "./base";
import { ArticlesClient } from "./articles";
import { AuthClient } from "./auth";
import { ChannelsClient } from "./channels";
import { CompetitionsClient } from "./competitions";
import { DiscoverClient } from "./discover";
import { DiscussionsClient } from "./discussions";
import { FollowsClient } from "./follows";
import { ProjectsClient } from "./projects";
import { MyProjectsClient } from "./my-projects";
import { MyReviewClient } from "./my-review";
import { NotificationsClient } from "./notifications";
import { UsersClient } from "./users";
import { TagsClient } from "./tags";

export class API {
  private client: APIClient;

  readonly articles: ArticlesClient;
  readonly auth: AuthClient;
  readonly channels: ChannelsClient;
  readonly competitions: CompetitionsClient;
  readonly discover: DiscoverClient;
  readonly discussions: DiscussionsClient;
  readonly follows: FollowsClient;
  readonly projects: ProjectsClient;
  readonly myProjects: MyProjectsClient;
  readonly myReview: MyReviewClient;
  readonly notifications: NotificationsClient;
  readonly users: UsersClient;
  readonly tags: TagsClient;

  constructor() {
    this.client = new APIClient();
    this.articles = new ArticlesClient(this.client);
    this.auth = new AuthClient(this.client);
    this.channels = new ChannelsClient(this.client);
    this.competitions = new CompetitionsClient(this.client);
    this.discover = new DiscoverClient(this.client);
    this.discussions = new DiscussionsClient(this.client);
    this.follows = new FollowsClient(this.client);
    this.projects = new ProjectsClient(this.client);
    this.myProjects = new MyProjectsClient(this.client);
    this.myReview = new MyReviewClient(this.client);
    this.notifications = new NotificationsClient(this.client);
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
