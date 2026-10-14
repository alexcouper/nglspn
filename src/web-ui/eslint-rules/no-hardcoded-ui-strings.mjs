// User-facing text in components must come from src/i18n/<area>/en.json through
// next-intl (useTranslations in client components, getTranslations on the
// server). This rule fails on text written straight into JSX so that English
// cannot creep back in once an area has been moved over.
//
// What counts as user-facing:
//   - JSX text children containing at least one letter: <p>Save</p>
//   - string literals as JSX children, including inside ?: and || / ??:
//     <p>{saving ? "Saving..." : "Save"}</p>
//   - string literals in attributes a person reads: alt, title, placeholder,
//     label, description, aria-label, …, plus any prop whose name ends in
//     Label/Text/Title/Message/Description/Placeholder/Hint/Heading/Caption.
//
// Not covered, by design: strings built outside JSX (toast titles, thrown
// errors, metadata objects). The nglspn-code-review skill checks those.

const HAS_LETTER = /\p{L}/u;

const DEFAULT_ATTRIBUTES = [
  "alt",
  "title",
  "placeholder",
  "label",
  "description",
  "aria-label",
  "aria-description",
  "aria-placeholder",
  "aria-roledescription",
  "aria-valuetext",
];

const ATTRIBUTE_SUFFIX = /(Label|Text|Title|Message|Description|Placeholder|Hint|Heading|Caption)$/;

function normalise(text) {
  return text.replace(/\s+/g, " ").trim();
}

/** String-bearing nodes an expression could render: literals, template text, either branch of ?:, both sides of || and ??. */
function* textLiterals(node) {
  if (!node) return;
  switch (node.type) {
    case "Literal":
      if (typeof node.value === "string") yield { node, text: node.value };
      return;
    case "TemplateLiteral": {
      // One report per template, with the holes shown as "…".
      const text = node.quasis.map((quasi) => quasi.value.cooked ?? "").join("…");
      if (HAS_LETTER.test(text)) yield { node, text };
      return;
    }
    case "ConditionalExpression":
      yield* textLiterals(node.consequent);
      yield* textLiterals(node.alternate);
      return;
    case "LogicalExpression":
      if (node.operator !== "&&") yield* textLiterals(node.left);
      yield* textLiterals(node.right);
      return;
    case "JSXExpressionContainer":
      yield* textLiterals(node.expression);
      return;
    case "TSAsExpression":
    case "TSNonNullExpression":
    case "ParenthesizedExpression":
      yield* textLiterals(node.expression);
      return;
    default:
      return;
  }
}

const rule = {
  meta: {
    type: "problem",
    docs: {
      description:
        "User-facing text must come from src/i18n/<area>/en.json via next-intl, not be written into JSX.",
    },
    schema: [
      {
        type: "object",
        properties: {
          attributes: { type: "array", items: { type: "string" } },
          allow: { type: "array", items: { type: "string" } },
        },
        additionalProperties: false,
      },
    ],
    messages: {
      text:
        'Hardcoded UI text "{{text}}". Add it to src/i18n/<area>/en.json and render it with t() from useTranslations (client) or getTranslations (server).',
      attribute:
        'Hardcoded UI text in {{attribute}}="{{text}}". Add it to src/i18n/<area>/en.json and pass t(...) instead.',
    },
  },

  create(context) {
    const options = context.options[0] ?? {};
    const attributes = new Set(options.attributes ?? DEFAULT_ATTRIBUTES);
    const allow = new Set((options.allow ?? []).map(normalise));

    function isUserFacing(text) {
      const clean = normalise(text);
      return HAS_LETTER.test(clean) && !allow.has(clean);
    }

    function isReadableAttribute(name) {
      return attributes.has(name) || ATTRIBUTE_SUFFIX.test(name);
    }

    return {
      JSXText(node) {
        if (isUserFacing(node.value)) {
          context.report({ node, messageId: "text", data: { text: normalise(node.value) } });
        }
      },

      JSXExpressionContainer(node) {
        const parentType = node.parent?.type;
        if (parentType !== "JSXElement" && parentType !== "JSXFragment") return;
        for (const { node: literal, text } of textLiterals(node)) {
          if (isUserFacing(text)) {
            context.report({ node: literal, messageId: "text", data: { text: normalise(text) } });
          }
        }
      },

      JSXAttribute(node) {
        if (node.name.type !== "JSXIdentifier" || !isReadableAttribute(node.name.name)) return;
        for (const { node: literal, text } of textLiterals(node.value)) {
          if (isUserFacing(text)) {
            context.report({
              node: literal,
              messageId: "attribute",
              data: { attribute: node.name.name, text: normalise(text) },
            });
          }
        }
      },
    };
  },
};

export default rule;
