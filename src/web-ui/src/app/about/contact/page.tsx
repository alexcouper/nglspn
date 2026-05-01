import { SITE_EMAIL } from "@/lib/constants";

export default function ContactPage() {
  return (
    <section className="py-12 px-4 sm:px-6 bg-white">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-lg font-semibold text-foreground tracking-tight mb-4">
          Get in touch
        </h2>
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground w-16">Discord</span>
            <a
              href="https://discord.gg/D47bQjaQ"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-accent hover:text-accent-hover transition-colors"
            >
              discord.gg/D47bQjaQ
            </a>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground w-16">Email</span>
            <a
              href={`mailto:${SITE_EMAIL}`}
              className="text-sm text-accent hover:text-accent-hover transition-colors"
            >
              {SITE_EMAIL}
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
