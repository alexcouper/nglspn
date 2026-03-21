# Accessibility Scanner

**URL:** https://github.com/koddsson/accessibility-scanner

## Database Description

Scans for accessibility issues in production, not via HTML linting. Ships scanner to production to scan pages as users navigate. Written from scratch for performance. Treats Accessibility violations as production errors. Started at GitHub, now being implemented at current job.

## Product Overview

Accessibility Scanner is an open-source JavaScript/TypeScript library that implements 60+ accessibility rules based on the axe-core ruleset and WCAG standards (2.0 and 2.1, Levels A and AA), as well as ACT (Automated Conformance Testing) rules. Unlike traditional HTML linters or CI-time scanners, this library is designed to be shipped to production and run in real browsers as users navigate, catching accessibility violations in the actual rendered DOM rather than in static markup. The scanner checks for a wide range of issues including missing alt text, improper heading order, invalid ARIA attributes and roles, insufficient color contrast, missing form labels, keyboard navigation problems, and language declaration issues. Results are categorized by impact level (Critical, Serious, Moderate, Minor), allowing teams to prioritize fixes. The philosophy behind the project is to treat accessibility violations as production errors on par with JavaScript exceptions or performance regressions -- something to be detected, reported, and fixed in real time. The project originated from work at GitHub and is now being implemented at the author's current workplace. It is written from scratch with performance as a key design goal, making it lightweight enough to run in production without degrading the user experience.

## Possible Categories

- **Dev Tools** - A developer-facing library that integrates into web applications to detect and report accessibility issues, fitting squarely into the development tooling space.
- **Accessibility** - The entire purpose of the project is to improve web accessibility by surfacing WCAG violations, making this a natural fit for an accessibility-focused category.
- **Open Source** - A fully open-source project on GitHub with community-oriented development, available for anyone to use, fork, and contribute to.
- **Quality & Testing** - Functions as a runtime testing and monitoring tool that treats accessibility violations as errors to be caught and fixed, aligning it with quality assurance and testing tooling.
