"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

const DISCUSSION_OPTIONS = [
  { value: "immediate", label: "Every time" },
  { value: "hourly", label: "Hourly" },
  { value: "daily", label: "Daily" },
  { value: "never", label: "Never" },
] as const;

const ARTICLE_OPTIONS = [
  { value: "hourly", label: "Hourly" },
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "never", label: "Never" },
] as const;

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

  return (
    <div className="bg-white rounded-xl border border-border p-5 mt-6">
      <h2 className="text-sm font-semibold text-foreground mb-1">Email preferences</h2>
      <p className="text-xs text-muted-foreground mb-3">
        Choose which project channels email you on the{" "}
        <Link href="/profile/following" className="text-accent hover:underline">
          Following
        </Link>{" "}
        page; control how often emails are sent below.
      </p>

      <CadenceSelector
        label="Discussion emails"
        description="How often to email you when someone comments on a discussion you're in."
        options={DISCUSSION_OPTIONS}
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
        label="Article emails"
        description="How often to summarise new articles from projects you follow."
        options={ARTICLE_OPTIONS}
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
