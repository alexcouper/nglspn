// Files that still contain hardcoded UI text. nglspn/no-hardcoded-ui-strings
// is switched off for them until they are moved over to src/i18n (issue #103).
//
// Only ever delete lines from this list. A new component is not on it, so the
// rule applies from its first line. eslint-rules/no-hardcoded-ui-strings.test.mjs
// fails if an entry names a file that no longer exists.
//
// Empty since the first migration pass; kept so the mechanism is there if a
// large pre-i18n component ever has to be brought in wholesale.
export const I18N_PENDING_FILES = [];
