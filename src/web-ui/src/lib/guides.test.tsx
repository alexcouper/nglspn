import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { GuideArticle, GuideIndex } from "@/components/guides/GuidePages";
import { guidesFor } from "@/content/guides";
import sitemap from "@/app/sitemap";
import robots from "@/app/robots";
import { generateStaticParams as englishParams } from "@/app/guides/[...slug]/page";
import { generateStaticParams as icelandicParams } from "@/app/is/guides/[...slug]/page";
import { SITE_URL } from "@/lib/constants";
import {
  guideMetadata,
  guideStructuredData,
  guideUrl,
  localizedGuides,
  localizeGuideLink,
} from "./guides";

describe("bilingual guide discovery", () => {
  it("prerenders both languages with matching topics and includes every URL in the sitemap", () => {
    const expected = guidesFor("en").map((guide) => ({ slug: guide.slug.split("/") }));
    expect(englishParams()).toEqual(expected);
    expect(icelandicParams()).toEqual(expected);
    const entries = sitemap();
    expect(new Set(entries.map((entry) => entry.url)).size).toBe(entries.length);
    for (const language of ["en", "is"] as const) {
      for (const slug of ["", ...guidesFor("en").map((guide) => guide.slug)]) {
        const url = `${SITE_URL}${guideUrl(language, slug)}`;
        expect(entries.find((entry) => entry.url === url)?.alternates?.languages).toEqual({
          en: `${SITE_URL}${guideUrl("en", slug)}`,
          is: `${SITE_URL}${guideUrl("is", slug)}`,
        });
      }
    }
    expect(robots().sitemap).toBe(`${SITE_URL}/sitemap.xml`);
    expect(entries.some((entry) => /my-projects|profile|login|register|create/.test(entry.url))).toBe(false);
  });

  it("keeps the hub/spoke graph connected and all in-content guide links valid", () => {
    for (const language of ["en", "is"] as const) {
      const localized = localizedGuides(language);
      const slugs = new Set(localized.map((guide) => guide.slug));
      expect(slugs.size).toBe(localized.length);
      for (const guide of localized) {
        const sectionIds = new Set(guide.sections.map((section) => section.id));
        expect(sectionIds.size).toBe(guide.sections.length);
        for (const slug of guide.related) expect(slugs.has(slug), slug).toBe(true);
        if (guide.kind === "spoke") {
          const parent = localized.find((entry) => entry.slug === guide.parent);
          expect(parent?.kind).toBe("hub");
          expect(guide.slug.startsWith(`${parent?.slug}/`)).toBe(true);
        } else {
          expect(localized.some((entry) => entry.parent === guide.slug)).toBe(true);
        }
        for (const section of guide.sections) {
          for (const match of section.body.matchAll(/\]\((\/guides\/[^)]+)\)/g)) {
            expect(slugs.has(match[1].replace("/guides/", "")), match[1]).toBe(true);
          }
        }
      }
    }
    expect(localizeGuideLink("/guides/share-a-side-project", "is")).toBe("/is/guides/share-a-side-project");
    expect(localizeGuideLink("/projects/example", "is")).toBe("/projects/example");
  });

  it("renders the full translated content, navigation, and valid schema without client JavaScript", () => {
    for (const language of ["en", "is"] as const) {
      const allGuides = localizedGuides(language);
      const index = document.createElement("div");
      index.innerHTML = renderToStaticMarkup(<GuideIndex language={language} />);
      expect(index.querySelector("main")?.lang).toBe(language);
      expect(index.querySelectorAll("h1")).toHaveLength(1);
      for (const guide of allGuides) {
        expect(index.querySelector(`a[href="${guideUrl(language, guide.slug)}"]`)).not.toBeNull();
        const page = document.createElement("div");
        page.innerHTML = renderToStaticMarkup(<GuideArticle guide={guide} language={language} />);
        expect(page.querySelector("main")?.lang).toBe(language);
        expect(page.querySelectorAll("h1")).toHaveLength(1);
        expect(page.querySelector("h1")?.textContent).toBe(guide.title);
        expect(page.textContent).toContain(guide.summary);
        expect(page.querySelector("time")?.dateTime).toBe(guide.updated);
        for (const section of guide.sections) {
          expect(page.querySelector(`#${section.id}`)?.textContent).toContain(section.title);
        }
        for (const link of page.querySelectorAll('a[href^="#"]')) {
          expect(page.querySelector(link.getAttribute("href")!)).not.toBeNull();
        }
        for (const locale of ["en", "is"] as const) {
          expect(page.querySelector(`a[hreflang="${locale}"]`)?.getAttribute("href")).toBe(guideUrl(locale, guide.slug));
        }
        if (language === "is") {
          expect(page.querySelector('a[href^="/guides/"]:not([hreflang])')).toBeNull();
          expect(guide.title).not.toBe(guidesFor("en").find((entry) => entry.slug === guide.slug)?.title);
        }
        const data = JSON.parse(page.querySelector('script[type="application/ld+json"]')!.textContent!);
        expect(data).toEqual(guideStructuredData(language, guide));
        expect(data["@graph"][1].inLanguage).toBe(language);
        expect(data["@graph"][1]["@type"]).toBe(guide.kind === "hub" ? "CollectionPage" : "Article");
      }
    }
  });

  it("uses self-canonicals, reciprocal language alternates and localized social metadata", () => {
    for (const language of ["en", "is"] as const) {
      for (const guide of [undefined, ...localizedGuides(language)]) {
        const breadcrumb = guideStructuredData(language, guide)["@graph"].find(
          (node) => node["@type"] === "BreadcrumbList",
        );
        if (guide) {
          expect(breadcrumb?.itemListElement).toHaveLength(guide.parent ? 3 : 2);
        } else {
          expect(breadcrumb).toBeUndefined();
        }
        const metadata = guideMetadata(language, guide);
        const url = `${SITE_URL}${guideUrl(language, guide?.slug)}`;
        expect(metadata.alternates?.canonical).toBe(url);
        expect(metadata.alternates?.languages).toEqual({
          en: `${SITE_URL}${guideUrl("en", guide?.slug)}`,
          is: `${SITE_URL}${guideUrl("is", guide?.slug)}`,
          "x-default": `${SITE_URL}${guideUrl("en", guide?.slug)}`,
        });
        expect(metadata.openGraph).toMatchObject({ title: metadata.title, description: metadata.description, url });
        expect(metadata.twitter).toMatchObject({ title: metadata.title, description: metadata.description });
      }
    }
  });
});
