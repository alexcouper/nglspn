import { SITE_EMAIL } from "@/lib/constants";

export function TipoffExplainer() {
  return (
    <div className="space-y-2">
      <p className="text-sm text-foreground">
        Community tip-offs are projects spotted and added by someone other
        than their makers.
      </p>
      <p className="text-sm text-muted-foreground">
        If this is your project, get in touch:{" "}
        <a
          href={`mailto:${SITE_EMAIL}`}
          className="text-accent hover:text-accent-hover underline underline-offset-2"
        >
          {SITE_EMAIL}
        </a>
      </p>
    </div>
  );
}
