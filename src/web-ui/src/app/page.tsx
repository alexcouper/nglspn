import Link from "next/link";
import { CompetitionHighlight } from "./components/CompetitionHighlight";
import { fetchActiveOrRecentCompetition } from "@/lib/api/server";
export const revalidate = 3600;

export default async function Home() {
  const { active, recent } = await fetchActiveOrRecentCompetition().catch(
    () => ({ active: undefined, recent: undefined })
  );
  return (
    <main className="min-h-screen">
      {/* Hero */}
      <section className="bg-nav-bg pt-32 pb-20 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-indigo-400 text-sm font-medium tracking-wide uppercase mb-4">
            Iceland&apos;s builder community
          </p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white mb-5 tracking-tight leading-[1.1]">
            Shine a light on
            <br />
            your work
          </h1>
          <p className="text-lg text-slate-400 max-w-xl mx-auto mb-10 leading-relaxed">
            A platform for Icelandic developers to showcase side projects,
            get feedback from the community, and compete for recognition.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link href="/submit" className="btn-primary text-base px-6 py-3">
              Submit Your Project
            </Link>
            <Link href="/projects" className="btn-ghost text-slate-400 hover:text-white text-base px-6 py-3">
              Explore Projects
            </Link>
          </div>
        </div>
      </section>

      {/* Competition highlight */}
      <section className="bg-white py-16 px-4 sm:px-6 border-b border-border">
        <div className="max-w-5xl mx-auto">
          <CompetitionHighlight active={active ?? null} recent={recent ?? null} />
        </div>
      </section>

      {/* Features */}
      <section className="bg-muted py-20 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight mb-3">
              Supporting Iceland&apos;s builder ecosystem
            </h2>
            <p className="text-muted-foreground max-w-lg mx-auto">
              Everything you need to share your work and grow with the community.
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
                Show Your Work
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                A space to showcase your side projects and early-stage ideas to the Icelandic tech community.
              </p>
            </div>

            <div className="bg-white rounded-xl border border-border p-7">
              <div className="w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center mb-4">
                <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
                </svg>
              </div>
              <h3 className="font-semibold text-foreground mb-2">
                Get Feedback
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Receive valuable feedback from fellow builders and compete for prizes in community competitions.
              </p>
            </div>

            <div className="bg-white rounded-xl border border-border p-7">
              <div className="w-10 h-10 rounded-lg bg-amber-50 flex items-center justify-center mb-4">
                <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
                </svg>
              </div>
              <h3 className="font-semibold text-foreground mb-2">
                Share & Grow
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Share your experience and skills. Learn from others. Grow your project with the community.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-white py-20 px-4 sm:px-6">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-2xl font-semibold text-foreground tracking-tight mb-3">
            Ready to share your project?
          </h2>
          <p className="text-muted-foreground mb-8">
            Join the community and get your work seen.
          </p>
          <Link href="/register" className="btn-primary text-base px-8 py-3">
            Get Started
          </Link>
        </div>
      </section>
    </main>
  );
}
