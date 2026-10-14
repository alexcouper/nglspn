import type { Messages } from "./messages";

// Typed keys: useTranslations("auth.login") and t("title") are checked against
// the JSON, so a typo or a deleted key fails `tsc`, not the user.
declare module "next-intl" {
  interface AppConfig {
    Locale: "en";
    Messages: Messages;
  }
}
