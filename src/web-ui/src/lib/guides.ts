import type { Metadata } from "next";
import { guidesFor, type Guide, type GuideLanguage } from "@/content/guides";
import { SITE_URL } from "@/lib/constants";
import guidesMessages from "@/i18n/guides/en.json";

export type { GuideLanguage };

// The guide chrome is the one part of the site already rendered in two
// languages, on /guides and /is/guides, with no locale routing to pick between
// them. The English copy lives with the other UI strings in
// src/i18n/guides/en.json; the Icelandic copy stays here until an is.json
// exists and the request locale decides. Both are typed against the English
// keys so they cannot drift apart.
type GuideChrome = typeof guidesMessages.chrome;

export const guideCopy: Record<GuideLanguage, GuideChrome> = {
  en: guidesMessages.chrome,
  is: {
    label: "Leiðarvísar samfélagsins",
    kicker: "Naglasúpan · Leiðarvísar samfélagsins",
    title: "Smíðaðu eitthvað. Deildu því sem þú lærir.",
    description: "Hagnýtir leiðarvísar um að finna íslensk hugbúnaðarverkefni, deila eigin verkum og leggja samfélagi Naglasúpunnar lið.",
    intro: "Upphafspunktur fyrir þig sem hefur verkefni að sýna, færni að bjóða eða langar að prófa eitthvað nýtt. Finndu næsta skref í íslensku hugbúnaðarsamfélagi.",
    overview: "Yfirlit",
    readOverview: "Lesa leiðarvísinn",
    inThisGuide: "Í þessum leiðarvísi",
    goDeeper: "Nánar um efnið",
    related: "Lesa áfram",
    byline: "Leiðarvísir frá Naglasúpunni",
    updated: "Uppfært",
    about: "Um Naglasúpuna",
    aboutText: "Naglasúpan sameinar fólk sem smíðar hugbúnað á Íslandi. Kynntu þér verkefnin, sýndu eigin verk og hjálpið hvert öðru áfram.",
    projects: "Skoða verkefni",
    purpose: "Tilgangur Naglasúpunnar",
    correction: "Viltu benda á leiðréttingu eða gagnlegt dæmi?",
    contact: "Hafðu samband",
    language: "Tungumál leiðarvísis",
    breadcrumb: "Staðsetning á vefnum",
  },
};

// Each language named in itself, for the switcher. Autonyms are the same
// whichever language the page is in, so they are not translated.
export const guideLanguageNames: Record<GuideLanguage, string> = {
  en: "English",
  is: "Íslenska",
};

export function guideUrl(language: GuideLanguage, slug = ""): string {
  return `${language === "is" ? "/is" : ""}/guides${slug ? `/${slug}` : ""}`;
}

export function localizedGuides(language: GuideLanguage): Guide[] {
  return guidesFor(language);
}

export function localizedGuide(language: GuideLanguage, slug: string): Guide | undefined {
  return localizedGuides(language).find((guide) => guide.slug === slug);
}

export function localizeGuideLink(href: string, language: GuideLanguage): string {
  return language === "is" && (href === "/guides" || href.startsWith("/guides/"))
    ? `/is${href}`
    : href;
}

export function guideMetadata(language: GuideLanguage, guide?: Guide): Metadata {
  const heading = guide?.title ?? guideCopy[language].label;
  const title = heading.includes("Naglasúpan") ? heading : `${heading} | Naglasúpan`;
  const description = guide?.description ?? guideCopy[language].description;
  const url = `${SITE_URL}${guideUrl(language, guide?.slug)}`;
  return {
    title,
    description,
    alternates: {
      canonical: url,
      languages: {
        en: `${SITE_URL}${guideUrl("en", guide?.slug)}`,
        is: `${SITE_URL}${guideUrl("is", guide?.slug)}`,
        "x-default": `${SITE_URL}${guideUrl("en", guide?.slug)}`,
      },
    },
    openGraph: {
      type: guide?.kind === "spoke" ? "article" : "website",
      title,
      description,
      url,
      siteName: "Naglasúpan",
      locale: language === "is" ? "is_IS" : "en_GB",
      alternateLocale: language === "is" ? "en_GB" : "is_IS",
      images: [{ url: "/icons/app/logo.png", alt: "Naglasúpan" }],
    },
    twitter: {
      card: "summary",
      title,
      description,
      images: ["/icons/app/logo.png"],
    },
  };
}

export function guideStructuredData(language: GuideLanguage, guide?: Guide) {
  const url = `${SITE_URL}${guideUrl(language, guide?.slug)}`;
  const allGuides = localizedGuides(language);
  const children = guide
    ? allGuides.filter((entry) => entry.parent === guide.slug)
    : allGuides.filter((entry) => entry.kind === "hub");
  const parent = guide?.parent ? localizedGuide(language, guide.parent) : undefined;
  const breadcrumbs = [
    { name: guideCopy[language].label, url: `${SITE_URL}${guideUrl(language)}` },
    ...(parent ? [{ name: parent.title, url: `${SITE_URL}${guideUrl(language, parent.slug)}` }] : []),
    ...(guide ? [{ name: guide.title, url }] : []),
  ];

  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": `${SITE_URL}/#organization`,
        name: "Naglasúpan",
        url: SITE_URL,
        logo: `${SITE_URL}/icons/app/logo.png`,
      },
      {
        "@type": guide?.kind === "spoke" ? "Article" : "CollectionPage",
        "@id": `${url}#content`,
        url,
        name: guide?.title ?? guideCopy[language].label,
        headline: guide?.title ?? guideCopy[language].label,
        description: guide?.description ?? guideCopy[language].description,
        inLanguage: language,
        ...(guide ? {
          dateModified: guide.updated,
          author: { "@id": `${SITE_URL}/#organization` },
        } : {}),
        publisher: { "@id": `${SITE_URL}/#organization` },
        ...(guide?.kind === "spoke" ? { mainEntityOfPage: url } : {
          mainEntity: {
            "@type": "ItemList",
            itemListElement: children.map((child, index) => ({
              "@type": "ListItem",
              position: index + 1,
              name: child.title,
              url: `${SITE_URL}${guideUrl(language, child.slug)}`,
            })),
          },
        }),
      },
      ...(breadcrumbs.length >= 2 ? [{
        "@type": "BreadcrumbList",
        itemListElement: breadcrumbs.map((crumb, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: crumb.name,
          item: crumb.url,
        })),
      }] : []),
    ],
  };
}
