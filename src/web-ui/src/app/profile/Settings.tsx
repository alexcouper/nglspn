"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

const NOTIFICATION_OPTIONS = [
  { value: "immediate", label: "Every time" },
  { value: "hourly", label: "Hourly" },
  { value: "daily", label: "Daily" },
  { value: "never", label: "Never" },
] as const;

interface SettingsProps {
  optInToExternalPromotions: boolean;
  notificationFrequency: string;
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
  optInToExternalPromotions,
  notificationFrequency,
}: SettingsProps) {
  const [externalPromotions, setExternalPromotions] = useState(optInToExternalPromotions);
  const [frequency, setFrequency] = useState(notificationFrequency);
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

  return (
    <div className="bg-white rounded-xl border border-border p-5 mt-6">
      <h2 className="text-sm font-semibold text-foreground mb-1">Email preferences</h2>
      <p className="text-xs text-muted-foreground mb-3">
        Choose which project channels email you — including Naglasúpan updates —
        on the{" "}
        <Link href="/profile/following" className="text-accent hover:underline">
          Following
        </Link>{" "}
        page.
      </p>

      <h2 className="text-sm font-semibold text-foreground mb-1 mt-6">Notifications</h2>
      <p className="text-xs text-muted-foreground mb-3">
        How often you receive discussion notifications
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
            {opt.label}
          </button>
        ))}
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
