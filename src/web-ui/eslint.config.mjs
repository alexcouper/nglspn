import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import noHardcodedUiStrings from "./eslint-rules/no-hardcoded-ui-strings.mjs";
import { I18N_PENDING_FILES } from "./eslint-rules/i18n-pending.mjs";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  // User-facing text goes through next-intl (src/i18n). Tests are fixtures, and
  // src/app/is/** is Icelandic guide content, not UI chrome — issue #103 leaves
  // it as it is until locale routing exists.
  {
    files: ["src/**/*.tsx"],
    ignores: ["src/**/*.test.tsx", "src/test/**", "src/app/is/**"],
    plugins: {
      nglspn: { rules: { "no-hardcoded-ui-strings": noHardcodedUiStrings } },
    },
    rules: {
      "nglspn/no-hardcoded-ui-strings": ["error", { allow: ["naglasúpan"] }],
    },
  },
  // ESLint rejects a config block with an empty `files`, so the exemption only
  // exists while there is something to exempt. Paths are globs, so the [slug]
  // in route directories has to be escaped or it is read as a character class.
  ...(I18N_PENDING_FILES.length > 0
    ? [
        {
          files: I18N_PENDING_FILES.map((file) => file.replace(/[[\]]/g, "\\$&")),
          rules: { "nglspn/no-hardcoded-ui-strings": "off" },
        },
      ]
    : []),
]);

export default eslintConfig;
