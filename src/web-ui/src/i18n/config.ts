export const locales = ["is", "en"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "is";

export const localeLabels: Record<Locale, string> = {
  is: "Íslenska",
  en: "English",
};
