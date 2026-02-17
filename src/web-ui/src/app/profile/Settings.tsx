"use client";

import { useState } from "react";
import { api } from "@/lib/api";

interface SettingsProps {
  emailOptInCompetitionResults: boolean;
  emailOptInPlatformUpdates: boolean;
  optInToExternalPromotions: boolean;
}

interface ToggleProps {
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

function Toggle({ label, description, checked, onChange, disabled }: ToggleProps) {
  return (
    <label className="flex items-center justify-between py-3.5 cursor-pointer group">
      <div className="pr-4">
        <div className="text-sm font-medium text-foreground">
          {label}
        </div>
        <div className="text-xs text-muted-foreground mt-0.5">{description}</div>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`
          relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent
          transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-accent/30 focus:ring-offset-2
          ${checked ? "bg-accent" : "bg-slate-200"}
          ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
        `}
      >
        <span
          className={`
            pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow ring-0
            transition duration-200 ease-in-out
            ${checked ? "translate-x-4" : "translate-x-0"}
          `}
        />
      </button>
    </label>
  );
}

export function Settings({
  emailOptInCompetitionResults,
  emailOptInPlatformUpdates,
  optInToExternalPromotions,
}: SettingsProps) {
  const [competitionResults, setCompetitionResults] = useState(emailOptInCompetitionResults);
  const [platformUpdates, setPlatformUpdates] = useState(emailOptInPlatformUpdates);
  const [externalPromotions, setExternalPromotions] = useState(optInToExternalPromotions);
  const [saving, setSaving] = useState<string | null>(null);

  const handleToggle = async (
    field: "email_opt_in_competition_results" | "email_opt_in_platform_updates" | "opt_in_to_external_promotions",
    value: boolean,
    setter: (v: boolean) => void
  ) => {
    setSaving(field);
    setter(value);

    try {
      await api.auth.updateCurrentUser({ [field]: value });
    } catch {
      setter(!value);
    } finally {
      setSaving(null);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-border p-5 mt-6">
      <h2 className="text-sm font-semibold text-foreground mb-1">Settings</h2>
      <p className="text-xs text-muted-foreground mb-3">Manage your email preferences</p>

      <div className="divide-y divide-border">
        <Toggle
          label="Competition results"
          description="Receive emails about competition outcomes and rankings"
          checked={competitionResults}
          onChange={(v) =>
            handleToggle("email_opt_in_competition_results", v, setCompetitionResults)
          }
          disabled={saving === "email_opt_in_competition_results"}
        />
        <Toggle
          label="Platform updates"
          description="Receive emails about new features and improvements"
          checked={platformUpdates}
          onChange={(v) =>
            handleToggle("email_opt_in_platform_updates", v, setPlatformUpdates)
          }
          disabled={saving === "email_opt_in_platform_updates"}
        />
      </div>

      <h2 className="text-sm font-semibold text-foreground mb-1 mt-6">Privacy</h2>
      <p className="text-xs text-muted-foreground mb-3">Manage your privacy preferences</p>

      <div className="divide-y divide-border">
        <Toggle
          label="External promotions"
          description="Allow your participation to be featured on external platforms like LinkedIn"
          checked={externalPromotions}
          onChange={(v) =>
            handleToggle("opt_in_to_external_promotions", v, setExternalPromotions)
          }
          disabled={saving === "opt_in_to_external_promotions"}
        />
      </div>
    </div>
  );
}
