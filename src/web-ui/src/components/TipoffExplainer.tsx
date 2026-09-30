import Link from "next/link";

import { SITE_EMAIL } from "@/lib/constants";

export function TipoffExplainer() {
  return (
    <div className="space-y-2">
      <p className="text-sm text-foreground">
        Community tip-offs are projects spotted and added by someone other
        than their makers.
      </p>
      <p className="text-sm text-muted-foreground">
        Know of one?{" "}
        <Link
          href="/create"
          className="text-accent hover:text-accent-hover underline underline-offset-2"
        >
          Add it as a tip-off
        </Link>
        .
      </p>
      <p className="text-sm text-muted-foreground">
        Made one of these projects? Email{" "}
        <a
          href={`mailto:${SITE_EMAIL}`}
          className="text-accent hover:text-accent-hover underline underline-offset-2"
        >
          {SITE_EMAIL}
        </a>{" "}
        to claim it.
      </p>
    </div>
  );
}
