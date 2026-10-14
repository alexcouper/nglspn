// One file per area, merged into a single object keyed by area. The area name is
// the namespace a component asks for: useTranslations("auth.login") reads
// auth/en.json → login. Adding an area means adding a directory here and one
// import line below; eslint-rules/no-hardcoded-ui-strings.test.mjs fails if a
// directory exists that this file does not import.
import about from "./about/en.json";
import articles from "./articles/en.json";
import auth from "./auth/en.json";
import common from "./common/en.json";
import competitions from "./competitions/en.json";
import discussions from "./discussions/en.json";
import feed from "./feed/en.json";
import guides from "./guides/en.json";
import images from "./images/en.json";
import myProjects from "./my-projects/en.json";
import notifications from "./notifications/en.json";
import profile from "./profile/en.json";
import projects from "./projects/en.json";

export const messages = {
  about,
  articles,
  auth,
  common,
  competitions,
  discussions,
  feed,
  guides,
  images,
  "my-projects": myProjects,
  notifications,
  profile,
  projects,
};

export type Messages = typeof messages;
