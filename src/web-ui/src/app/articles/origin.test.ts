import { describe, expect, it } from "vitest";

import type { Project, PublicUserProfile } from "@/lib/api";

import { authorContainer, projectContainer, type Container } from "./container";
import { resolveOrigin, withOrigin } from "./origin";

function project(overrides: Partial<Project> = {}): Container {
  return projectContainer({
    id: "p-1",
    slug: "hot-spring-finder",
    title: "Hot Spring Finder",
    ...overrides,
  } as Project);
}

function author(): Container {
  return authorContainer({
    id: "u-1",
    first_name: "Sigrún",
    last_name: "Haraldsdóttir",
  } as PublicUserProfile);
}

describe("resolveOrigin", () => {
  it("sends a reader who came from the feed back to the feed", () => {
    expect(resolveOrigin("latest", project())).toEqual({
      kind: "latest",
      href: "/latest",
    });
  });

  it("falls back to the project when there is no parameter", () => {
    expect(resolveOrigin(undefined, project())).toEqual({
      kind: "container",
      href: "/projects/hot-spring-finder#articles",
      title: "Hot Spring Finder",
    });
  });

  it("falls back to the author's profile for an author-owned article", () => {
    expect(resolveOrigin(undefined, author())).toEqual({
      kind: "container",
      href: "/users/u-1#profile-articles",
      title: "Sigrún Haraldsdóttir",
    });
  });

  it("falls back to the project rather than trusting an unknown value", () => {
    expect(resolveOrigin("https://evil.test", project()).href).toBe(
      "/projects/hot-spring-finder#articles",
    );
    expect(resolveOrigin("constructor", project()).kind).toBe("container");
  });

  it("takes the first value when the parameter is repeated", () => {
    expect(resolveOrigin(["latest", "whatever"], project()).kind).toBe("latest");
  });

  it("addresses a project by id when it has no slug yet", () => {
    expect(resolveOrigin(undefined, project({ slug: null })).href).toBe(
      "/projects/p-1#articles",
    );
  });
});

describe("withOrigin", () => {
  it("marks a link with where it was followed from", () => {
    expect(withOrigin("/projects/a/articles/b", "latest")).toBe(
      "/projects/a/articles/b?from=latest",
    );
  });
});
