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
              href="https://discord.gg/DqUV64g7JE"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-accent hover:text-accent-hover transition-colors"
            >
              discord.gg/DqUV64g7JE
            </a>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground w-16">Email</span>
            <a
              href="mailto:alex@naglasupan.is"
              className="text-sm text-accent hover:text-accent-hover transition-colors"
            >
              alex@naglasupan.is
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
