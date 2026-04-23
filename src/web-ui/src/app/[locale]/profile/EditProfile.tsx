"use client";

import { useTranslations } from "next-intl";
import { Translatable } from "@/components/Translatable";

export interface ProfileFormData {
  first_name: string;
  last_name: string;
  info: string;
}

interface EditProfileProps {
  formData: ProfileFormData;
  onChange: (data: ProfileFormData) => void;
  email: string;
}

export function EditProfile({ formData, onChange, email }: EditProfileProps) {
  const t = useTranslations();
  const handleChange = (field: keyof ProfileFormData, value: string) => {
    onChange({ ...formData, [field]: value });
  };

  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs text-muted-foreground">Email: {email}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="firstName" className="label">
            <Translatable tKey="profile.firstNameLabel">{t("profile.firstNameLabel")}</Translatable>
          </label>
          <input
            type="text"
            id="firstName"
            value={formData.first_name}
            onChange={(e) => handleChange("first_name", e.target.value)}
            className="input"
            placeholder={t("profile.firstNamePlaceholder")}
          />
        </div>

        <div>
          <label htmlFor="lastName" className="label">
            <Translatable tKey="profile.lastNameLabel">{t("profile.lastNameLabel")}</Translatable>
          </label>
          <input
            type="text"
            id="lastName"
            value={formData.last_name}
            onChange={(e) => handleChange("last_name", e.target.value)}
            className="input"
            placeholder={t("profile.lastNamePlaceholder")}
          />
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label htmlFor="info" className="label mb-0">
            <Translatable tKey="profile.aboutLabel">{t("profile.aboutLabel")}</Translatable>
          </label>
          <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
            <Translatable tKey="profile.markdownBadge">{t("profile.markdownBadge")}</Translatable>
          </span>
        </div>
        <textarea
          id="info"
          rows={6}
          value={formData.info}
          onChange={(e) => handleChange("info", e.target.value)}
          className="input resize-none"
          placeholder={t("profile.aboutPlaceholder")}
        />
        <p className="text-xs text-muted-foreground mt-1.5">
          <Translatable tKey="profile.aboutHelper">{t("profile.aboutHelper")}</Translatable>
        </p>
      </div>
    </div>
  );
}
