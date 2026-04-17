import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-border bg-white mt-auto">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        <div className="flex justify-end">
          <nav className="flex flex-wrap justify-end gap-x-6 gap-y-2 text-sm" aria-label="Footer">
            <Link
              href="/about"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              About
            </Link>
            <Link
              href="/privacy"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Privacy
            </Link>
            <a
              href="https://discord.gg/D47bQjaQ"
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Discord
            </a>
          </nav>
        </div>
      </div>
    </footer>
  );
}
