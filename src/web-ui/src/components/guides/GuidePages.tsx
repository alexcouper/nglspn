import Link from "next/link";
import ReactMarkdown from "react-markdown";
import type { Guide } from "@/content/guides";
import {
  guideCopy,
  guideStructuredData,
  guideUrl,
  localizedGuide,
  localizedGuides,
  localizeGuideLink,
  type GuideLanguage,
} from "@/lib/guides";

function StructuredData({ language, guide }: { language: GuideLanguage; guide?: Guide }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify(guideStructuredData(language, guide)).replace(/</g, "\\u003c"),
      }}
    />
  );
}

function LanguageSwitch({ language, slug }: { language: GuideLanguage; slug?: string }) {
  return (
    <nav aria-label={guideCopy[language].language} className="flex shrink-0 gap-3 text-sm">
      {(["en", "is"] as const).map((locale) => (
        <a
          key={locale}
          href={guideUrl(locale, slug)}
          hrefLang={locale}
          lang={locale}
          aria-current={language === locale ? "page" : undefined}
          className={language === locale ? "font-semibold text-foreground underline underline-offset-4" : "text-muted-foreground hover:text-foreground"}
        >
          {locale === "en" ? "English" : "Íslenska"}
        </a>
      ))}
    </nav>
  );
}

function GuideCard({ guide, language }: { guide: Guide; language: GuideLanguage }) {
  return (
    <Link href={guideUrl(language, guide.slug)} className="group block rounded-xl border border-border bg-white p-6 transition-colors hover:border-accent focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent">
      <h3 className="text-lg font-semibold leading-snug text-foreground group-hover:text-accent-hover">{guide.title}</h3>
      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{guide.description}</p>
      <span aria-hidden="true" className="mt-4 block text-accent">→</span>
    </Link>
  );
}

export function GuideIndex({ language }: { language: GuideLanguage }) {
  const copy = guideCopy[language];
  const allGuides = localizedGuides(language);
  const hubs = allGuides.filter((guide) => guide.kind === "hub");
  return (
    <main lang={language} className="bg-muted pt-14">
      <StructuredData language={language} />
      <div className="border-b border-border bg-white px-4 sm:px-6">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 py-5">
          <p className="text-sm font-medium">{copy.label}</p>
          <LanguageSwitch language={language} />
        </div>
      </div>
      <header className="bg-nav-bg px-4 py-16 sm:px-6 sm:py-20">
        <div className="mx-auto max-w-6xl">
          <p className="mb-5 text-sm font-medium tracking-wide text-indigo-300">Naglasúpan · {copy.label}</p>
          <h1 className="max-w-3xl text-4xl font-bold leading-tight tracking-tight text-white sm:text-5xl">{copy.title}</h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-slate-300">{copy.intro}</p>
          <Link href="/projects" className="mt-8 inline-flex items-center gap-2 text-sm font-medium text-indigo-200 underline underline-offset-4 hover:text-white">
            {copy.projects} <span aria-hidden="true">↗</span>
          </Link>
        </div>
      </header>
      <div className="mx-auto max-w-6xl space-y-14 px-4 py-14 sm:px-6">
        {hubs.map((hub, index) => (
          <section key={hub.slug} aria-labelledby={`hub-${hub.slug}`} className="grid gap-6 lg:grid-cols-[1fr_1.4fr] lg:gap-12">
            <div>
              <p className="mb-3 font-mono text-sm text-muted-foreground">0{index + 1} / {copy.overview}</p>
              <h2 id={`hub-${hub.slug}`} className="text-2xl font-semibold tracking-tight">{hub.title}</h2>
              <p className="mt-4 leading-relaxed text-muted-foreground">{hub.description}</p>
              <Link href={guideUrl(language, hub.slug)} className="mt-5 inline-block font-medium text-accent-hover underline underline-offset-4">{copy.readOverview} <span aria-hidden="true">→</span></Link>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              {allGuides.filter((guide) => guide.parent === hub.slug).map((guide) => (
                <GuideCard key={guide.slug} guide={guide} language={language} />
              ))}
            </div>
          </section>
        ))}
        <aside className="rounded-xl border border-border bg-white p-6 sm:p-8">
          <h2 className="text-xl font-semibold">{copy.about}</h2>
          <p className="mt-3 max-w-3xl leading-relaxed text-muted-foreground">{copy.aboutText}</p>
          <Link href="/about/why" className="mt-4 inline-block text-accent-hover underline underline-offset-4">{copy.purpose}</Link>
        </aside>
      </div>
    </main>
  );
}

export function GuideArticle({ guide, language }: { guide: Guide; language: GuideLanguage }) {
  const copy = guideCopy[language];
  const parent = guide.parent ? localizedGuide(language, guide.parent) : undefined;
  const spokes = localizedGuides(language).filter((entry) => entry.parent === guide.slug);
  const related = guide.related.map((slug) => localizedGuide(language, slug)).filter((entry): entry is Guide => Boolean(entry));
  const updated = new Intl.DateTimeFormat(language === "is" ? "is-IS" : "en-GB", {
    day: "numeric", month: "long", year: "numeric", timeZone: "UTC",
  }).format(new Date(`${guide.updated}T00:00:00Z`));

  return (
    <main lang={language} className="bg-white pt-14">
      <StructuredData language={language} guide={guide} />
      <div className="border-b border-border px-4 sm:px-6">
        <div className="mx-auto flex max-w-6xl flex-wrap items-start justify-between gap-4 py-5">
          <nav aria-label={copy.breadcrumb} className="max-w-3xl text-sm text-muted-foreground">
            <ol className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <li><Link href={guideUrl(language)} className="hover:text-foreground underline underline-offset-4">{copy.label}</Link></li>
              {parent && <li><span aria-hidden="true" className="mr-2">/</span><Link href={guideUrl(language, parent.slug)} className="hover:text-foreground underline underline-offset-4">{parent.title}</Link></li>}
              <li aria-current="page"><span aria-hidden="true" className="mr-2">/</span>{guide.title}</li>
            </ol>
          </nav>
          <LanguageSwitch language={language} slug={guide.slug} />
        </div>
      </div>
      <article className="mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-16">
        <header className="max-w-3xl">
          <p className="mb-4 text-sm font-medium text-accent-hover">{copy.byline}</p>
          <h1 className="text-3xl font-bold leading-tight tracking-tight sm:text-4xl lg:text-5xl">{guide.title}</h1>
          <p className="mt-6 text-lg leading-relaxed text-slate-600">{guide.summary}</p>
          <p className="mt-5 text-sm text-muted-foreground">{copy.updated} <time dateTime={guide.updated}>{updated}</time></p>
        </header>
        <div className="mt-10 grid items-start gap-10 lg:grid-cols-[minmax(0,1fr)_16rem] lg:gap-16">
          <nav aria-label={copy.inThisGuide} className="rounded-xl border border-border bg-muted p-5 lg:sticky lg:top-20 lg:col-start-2 lg:row-start-1">
            <h2 className="mb-3 text-sm font-semibold">{copy.inThisGuide}</h2>
            <ul className="space-y-3 text-sm leading-relaxed">
              {guide.sections.map((section) => <li key={section.id}><a href={`#${section.id}`} className="text-slate-600 hover:text-accent-hover underline underline-offset-4">{section.title}</a></li>)}
              {spokes.length > 0 && <li><a href="#explore-topic" className="text-slate-600 hover:text-accent-hover underline underline-offset-4">{copy.goDeeper}</a></li>}
            </ul>
          </nav>
          <div className="min-w-0 space-y-10 lg:col-start-1 lg:row-start-1">
            {guide.sections.map((section) => (
              <section key={section.id} id={section.id} aria-labelledby={`${section.id}-title`} className="scroll-mt-24">
                <h2 id={`${section.id}-title`} className="mb-4 text-2xl font-semibold tracking-tight">{section.title}</h2>
                <div className="markdown">
                  <ReactMarkdown components={{ a: ({ href, children }) => {
                    const url = localizeGuideLink(href ?? "", language);
                    return url.startsWith("/") ? <Link href={url}>{children}</Link> : <a href={url}>{children}</a>;
                  } }}>{section.body}</ReactMarkdown>
                </div>
              </section>
            ))}
            {spokes.length > 0 && (
              <section id="explore-topic" className="scroll-mt-24" aria-labelledby="explore-topic-title">
                <h2 id="explore-topic-title" className="mb-5 text-2xl font-semibold">{copy.goDeeper}</h2>
                <div className="grid gap-4 sm:grid-cols-2">{spokes.map((spoke) => <GuideCard key={spoke.slug} guide={spoke} language={language} />)}</div>
              </section>
            )}
            <div className="rounded-xl bg-accent-subtle p-6">
              <Link href={guide.action.href} className="btn-primary">{guide.action.label} <span aria-hidden="true">→</span></Link>
              <p className="mt-5 text-sm leading-relaxed text-slate-600">{copy.correction} <Link href="/about/contact" className="text-accent-hover underline underline-offset-4">{copy.contact}</Link>.</p>
            </div>
          </div>
        </div>
      </article>
      <section className="border-t border-border bg-muted px-4 py-12 sm:px-6" aria-labelledby="related-guides">
        <div className="mx-auto max-w-6xl">
          <h2 id="related-guides" className="mb-6 text-2xl font-semibold">{copy.related}</h2>
          <div className="grid gap-4 sm:grid-cols-2">{related.map((entry) => <GuideCard key={entry.slug} guide={entry} language={language} />)}</div>
        </div>
      </section>
    </main>
  );
}
