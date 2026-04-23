import { getTranslations } from "next-intl/server";
import { Translatable } from "@/components/Translatable";

export default async function AboutPage() {
  const t = await getTranslations();
  return (
    <section className="bg-muted py-20 px-4 sm:px-6">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight mb-3">
            <Translatable tKey="about.heading">{t("about.heading")}</Translatable>
          </h2>
          <p className="text-muted-foreground max-w-lg mx-auto">
            <Translatable tKey="about.subheading">{t("about.subheading")}</Translatable>
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          <div className="bg-white rounded-xl border border-border p-7">
            <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center mb-4">
              <svg className="w-5 h-5 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
              </svg>
            </div>
            <h3 className="font-semibold text-foreground mb-2">
              <Translatable tKey="about.section1.heading">{t("about.section1.heading")}</Translatable>
            </h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              <Translatable tKey="about.section1.description">{t("about.section1.description")}</Translatable>
            </p>
          </div>

          <div className="bg-white rounded-xl border border-border p-7">
            <div className="w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center mb-4">
              <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
              </svg>
            </div>
            <h3 className="font-semibold text-foreground mb-2">
              <Translatable tKey="about.section2.heading">{t("about.section2.heading")}</Translatable>
            </h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              <Translatable tKey="about.section2.description">{t("about.section2.description")}</Translatable>
            </p>
          </div>

          <div className="bg-white rounded-xl border border-border p-7">
            <div className="w-10 h-10 rounded-lg bg-amber-50 flex items-center justify-center mb-4">
              <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
              </svg>
            </div>
            <h3 className="font-semibold text-foreground mb-2">
              <Translatable tKey="about.section3.heading">{t("about.section3.heading")}</Translatable>
            </h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              <Translatable tKey="about.section3.description">{t("about.section3.description")}</Translatable>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
