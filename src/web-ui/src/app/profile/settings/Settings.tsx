"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";

const DISCUSSION_FREQUENCIES = ["immediate", "hourly", "daily", "never"] as const;

const ARTICLE_FREQUENCIES = ["hourly", "daily", "weekly", "never"] as const;

interface SettingsProps {
  optInToExternalPromotions: boolean;
  discussionEmailFrequency: string;
  articleEmailFrequency: string;
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

interface CadenceSelectorProps<TValues extends readonly { value: string; label: string }[]> {
  label: string;
  description: string;
  options: TValues;
  value: string;
  saving: boolean;
  onChange: (next: string) => Promise<void>;
}

function CadenceSelector<T extends readonly { value: string; label: string }[]>({
  label,
  description,
  options,
  value,
  saving,
  onChange,
}: CadenceSelectorProps<T>) {
  return (
    <div className="mt-5">
      <h3 className="text-sm font-medium text-foreground">{label}</h3>
      <p className="text-xs text-muted-foreground mt-0.5 mb-2">{description}</p>
      <div className="flex rounded-lg border border-border overflow-hidden">
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            disabled={saving}
            onClick={() => {
              if (opt.value === value) return;
              void onChange(opt.value);
            }}
            className={`
              flex-1 py-2 text-xs font-medium transition-colors
              ${
                value === opt.value
                  ? "bg-accent text-white"
                  : "bg-white text-muted-foreground hover:bg-muted hover:text-foreground"
              }
              ${saving ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
            `}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function Settings({
  optInToExternalPromotions,
  discussionEmailFrequency,
  articleEmailFrequency,
}: SettingsProps) {
  const t = useTranslations("profile.settings");
  const [externalPromotions, setExternalPromotions] = useState(optInToExternalPromotions);
  const [discussionFreq, setDiscussionFreq] = useState(discussionEmailFrequency);
  const [articleFreq, setArticleFreq] = useState(articleEmailFrequency);
  const [saving, setSaving] = useState<string | null>(null);

  const handleToggle = async (
    field: "opt_in_to_external_promotions",
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

  const updateCadence = async (
    field: "discussion_email_frequency" | "article_email_frequency",
    next: string,
    setter: (v: string) => void,
    previous: string
  ) => {
    setter(next);
    setSaving(field);
    try {
      await api.auth.updateCurrentUser({ [field]: next });
    } catch {
      setter(previous);
    } finally {
      setSaving(null);
    }
  };

  const discussionOptions = DISCUSSION_FREQUENCIES.map((value) => ({
    value,
    label: t(`frequency.${value}`),
  }));
  const articleOptions = ARTICLE_FREQUENCIES.map((value) => ({
    value,
    label: t(`frequency.${value}`),
  }));

  return (
    <div className="bg-white rounded-xl border border-border p-5">
      <h2 className="text-sm font-semibold text-foreground mb-1">{t("emailPreferences.title")}</h2>
      <p className="text-xs text-muted-foreground mb-3">
        {t.rich("emailPreferences.hint", {
          link: (chunks) => (
            <Link href="/profile/following" className="text-accent hover:underline">
              {chunks}
            </Link>
          ),
        })}
      </p>

      <CadenceSelector
        label={t("discussionEmails.label")}
        description={t("discussionEmails.description")}
        options={discussionOptions}
        value={discussionFreq}
        saving={saving === "discussion_email_frequency"}
        onChange={(next) =>
          updateCadence(
            "discussion_email_frequency",
            next,
            setDiscussionFreq,
            discussionFreq
          )
        }
      />

      <CadenceSelector
        label={t("articleEmails.label")}
        description={t("articleEmails.description")}
        options={articleOptions}
        value={articleFreq}
        saving={saving === "article_email_frequency"}
        onChange={(next) =>
          updateCadence(
            "article_email_frequency",
            next,
            setArticleFreq,
            articleFreq
          )
        }
      />

      <h2 className="text-sm font-semibold text-foreground mb-1 mt-6">{t("privacy.title")}</h2>
      <p className="text-xs text-muted-foreground mb-3">{t("privacy.hint")}</p>

      <div className="divide-y divide-border">
        <Toggle
          label={t("externalPromotions.label")}
          description={t("externalPromotions.description")}
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
