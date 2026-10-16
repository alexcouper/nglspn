import { beforeEach, describe, expect, it, vi } from "vitest";
import { ArticlesClient } from "./articles";
import { FollowsClient } from "./follows";
import type { APIClient } from "./base";

// The clients are URL builders over one `request`; these pin the addresses,
// which the backend's routers are the other half of.
function fakeClient() {
  const request = vi.fn().mockResolvedValue({});
  return { request, client: { request } as unknown as APIClient };
}

function calledPath(request: ReturnType<typeof vi.fn>): string {
  return request.mock.calls[0][0] as string;
}

function calledMethod(request: ReturnType<typeof vi.fn>): string | undefined {
  return (request.mock.calls[0][1] as RequestInit | undefined)?.method;
}

describe("ArticlesClient", () => {
  let request: ReturnType<typeof vi.fn>;
  let articles: ArticlesClient;

  beforeEach(() => {
    const fake = fakeClient();
    request = fake.request;
    articles = new ArticlesClient(fake.client);
  });

  it("addresses an article by id alone once it exists", async () => {
    await articles.get("a-1");
    expect(calledPath(request)).toBe("/api/articles/a-1");
  });

  it("patches, publishes and deletes by id", async () => {
    await articles.update("a-1", { title: "x" });
    expect(calledPath(request)).toBe("/api/articles/a-1");
    expect(calledMethod(request)).toBe("PATCH");

    request.mockClear();
    await articles.publish("a-1");
    expect(calledPath(request)).toBe("/api/articles/a-1/publish");

    request.mockClear();
    await articles.delete("a-1");
    expect(calledMethod(request)).toBe("DELETE");
  });

  it("creates a project article under its project", async () => {
    await articles.create("my-project", { channel_id: "c-1", title: "", body: "" });
    expect(calledPath(request)).toBe("/api/projects/my-project/articles");
  });

  it("creates and lists the caller's own articles under /me", async () => {
    await articles.createOwn({ title: "Mine", body: "" });
    expect(calledPath(request)).toBe("/api/auth/me/articles");
    expect(calledMethod(request)).toBe("POST");

    request.mockClear();
    await articles.listOwn();
    expect(calledPath(request)).toBe("/api/auth/me/articles");
  });

  it("reads by slug under the project or the author", async () => {
    await articles.getBySlug("my-project", "hello");
    expect(calledPath(request)).toBe("/api/projects/my-project/articles/by-slug/hello");

    request.mockClear();
    await articles.getBySlugForUser("u-1", "hello");
    expect(calledPath(request)).toBe("/api/users/u-1/articles/by-slug/hello");
  });

  it("addresses images under the article that owns them", async () => {
    await articles.getImageUploadUrl("a-1", "f.png", "image/png", 10);
    expect(calledPath(request)).toBe("/api/articles/a-1/images/upload-url");

    request.mockClear();
    await articles.completeImageUpload("a-1", "i-1", { width: 1, height: 1 });
    expect(calledPath(request)).toBe("/api/articles/a-1/images/i-1/complete");

    request.mockClear();
    await articles.deleteImage("a-1", "i-1");
    expect(calledPath(request)).toBe("/api/articles/a-1/images/i-1");
  });
});

describe("FollowsClient", () => {
  it("follows and unfollows a person under their profile", async () => {
    const { request, client } = fakeClient();
    const follows = new FollowsClient(client);

    await follows.followUser("u-1");
    expect(calledPath(request)).toBe("/api/users/u-1/follow");
    expect(calledMethod(request)).toBe("POST");

    request.mockClear();
    await follows.unfollowUser("u-1");
    expect(calledMethod(request)).toBe("DELETE");

    request.mockClear();
    await follows.unfollowUserChannel("u-1", "c-1");
    expect(calledPath(request)).toBe("/api/users/u-1/follow/channels/c-1");
  });
});
