"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { Translatable } from "@/components/Translatable";

const NOTIFICATION_OPTIONS = [
  { value: "immediate", tKey: "profile.settings.notificationImmediate" },
  { value: "hourly", tKey: "profile.settings.notificationHourly" },
  { value: "daily", tKey: "profile.settings.notificationDaily" },
  { value: "never", tKey: "profile.settings.notificationNever" },
] as const;

interface SettingsProps {
  emailOptInCompetitionResults: boolean;
  emailOptInPlatformUpdates: boolean;
  optInToExternalPromotions: boolean;
  notificationFrequency: string;
}

interface ToggleProps {
  labelKey: string;
  label: string;
  descriptionKey: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

function Toggle({ labelKey, label, descriptionKey, description, checked, onChange, disabled }: ToggleProps) {
  return (
    <label className="flex items-center justify-between py-3.5 cursor-pointer group">
      <div className="pr-4">
        <div className="text-sm font-medium text-foreground">
          <Translatable tKey={labelKey}>{label}</Translatable>
        </div>
        <div className="text-xs text-muted-foreground mt-0.5">
          <Translatable tKey={descriptionKey}>{description}</Translatable>
        </div>
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
  notificationFrequency,
}: SettingsProps) {
  const t = useTranslations();
  const [competitionResults, setCompetitionResults] = useState(emailOptInCompetitionResults);
  const [platformUpdates, setPlatformUpdates] = useState(emailOptInPlatformUpdates);
  const [externalPromotions, setExternalPromotions] = useState(optInToExternalPromotions);
  const [frequency, setFrequency] = useState(notificationFrequency);
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
      <h2 className="text-sm font-semibold text-foreground mb-1">
        <Translatable tKey="profile.settings.heading">{t("profile.settings.heading")}</Translatable>
      </h2>
      <p className="text-xs text-muted-foreground mb-3">
        <Translatable tKey="profile.settings.description">{t("profile.settings.description")}</Translatable>
      </p>

      <div className="divide-y divide-border">
        <Toggle
          labelKey="profile.settings.competitionResults"
          label={t("profile.settings.competitionResults")}
          descriptionKey="profile.settings.competitionResultsDescription"
          description={t("profile.settings.competitionResultsDescription")}
          checked={competitionResults}
          onChange={(v) =>
            handleToggle("email_opt_in_competition_results", v, setCompetitionResults)
          }
          disabled={saving === "email_opt_in_competition_results"}
        />
        <Toggle
          labelKey="profile.settings.platformUpdates"
          label={t("profile.settings.platformUpdates")}
          descriptionKey="profile.settings.platformUpdatesDescription"
          description={t("profile.settings.platformUpdatesDescription")}
          checked={platformUpdates}
          onChange={(v) =>
            handleToggle("email_opt_in_platform_updates", v, setPlatformUpdates)
          }
          disabled={saving === "email_opt_in_platform_updates"}
        />
      </div>

      <h2 className="text-sm font-semibold text-foreground mb-1 mt-6">
        <Translatable tKey="profile.settings.notificationsHeading">{t("profile.settings.notificationsHeading")}</Translatable>
      </h2>
      <p className="text-xs text-muted-foreground mb-3">
        <Translatable tKey="profile.settings.notificationsDescription">{t("profile.settings.notificationsDescription")}</Translatable>
      </p>

      <div className="flex rounded-lg border border-border overflow-hidden">
        {NOTIFICATION_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            disabled={saving === "notification_frequency"}
            onClick={async () => {
              if (opt.value === frequency) return;
              const prev = frequency;
              setFrequency(opt.value);
              setSaving("notification_frequency");
              try {
                await api.auth.updateCurrentUser({ notification_frequency: opt.value });
              } catch {
                setFrequency(prev);
              } finally {
                setSaving(null);
              }
            }}
            className={`
              flex-1 py-2 text-xs font-medium transition-colors
              ${
                frequency === opt.value
                  ? "bg-accent text-white"
                  : "bg-white text-muted-foreground hover:bg-muted hover:text-foreground"
              }
              ${saving === "notification_frequency" ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
            `}
          >
            <Translatable tKey={opt.tKey}>{t(opt.tKey)}</Translatable>
          </button>
        ))}
      </div>

      <h2 className="text-sm font-semibold text-foreground mb-1 mt-6">
        <Translatable tKey="profile.settings.privacyHeading">{t("profile.settings.privacyHeading")}</Translatable>
      </h2>
      <p className="text-xs text-muted-foreground mb-3">
        <Translatable tKey="profile.settings.privacyDescription">{t("profile.settings.privacyDescription")}</Translatable>
      </p>

      <div className="divide-y divide-border">
        <Toggle
          labelKey="profile.settings.externalPromotions"
          label={t("profile.settings.externalPromotions")}
          descriptionKey="profile.settings.externalPromotionsDescription"
          description={t("profile.settings.externalPromotionsDescription")}
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
