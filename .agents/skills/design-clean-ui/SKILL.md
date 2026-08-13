---
name: design-clean-ui
description: Design, build, review, or refine clean responsive product interfaces in an existing frontend project using a self-contained UX/UI system. Use for dashboards, admin and commerce applications, authentication, profiles, forms, data tables, navigation shells, Light/Dark themes, responsive behavior, Tailwind utility styling, Lucide icons, Toast feedback, or when a project needs a coherent UI foundation without an external design file.
---

# Design Clean UI

Create production-ready product UI from the specification bundled in this
skill. The consuming project does not need this repository, its demo source, or
an external design file.

Preserve the system's character: calm whitespace, restrained surfaces, clear
hierarchy, compact data controls, responsive composition, Light/Dark parity,
and explicit interaction feedback. Adapt copy, brand, data, routes, and
framework syntax to the host project.

## Read the relevant references

- Always read [references/project-integration.md](references/project-integration.md)
  before editing a consuming project.
- Read [references/design-language.md](references/design-language.md) when
  establishing tokens, typography, dimensions, spacing, themes, or responsive
  behavior.
- Read [references/implementation-style.md](references/implementation-style.md)
  before writing frontend code.
- Read [references/component-patterns.md](references/component-patterns.md)
  when composing screens or implementing interactions.

These references are authoritative and self-contained. Source files from this
repository may be inspected while developing the skill, but they are never a
runtime or usage requirement.

## Workflow

1. Inspect the host project's instructions, framework, styling system, routes,
   components, tokens, assets, data contracts, and existing behavior.
2. Define the requested screens, user tasks, states, variants, and observable
   success checks. Ask only when a missing product decision would materially
   change the result.
3. Map the bundled semantic design system onto existing host conventions. Keep
   host branding and functional requirements; do not import demo branding.
4. Establish the smallest missing foundations, then implement shared shell and
   primitives before page composition when the scope needs them.
5. Build one responsive, theme-aware component tree. Connect real routes and
   data when available; never leave a visible control inert.
6. Verify hierarchy, spacing, typography, themes, breakpoints, keyboard access,
   loading/empty/error/success states, and interactions.
7. Run the host project's lint, typecheck, tests, and production build in
   proportion to the change. Report checks and any intentional deviations.

## Non-negotiable outcomes

- The result looks like one coherent product, not a collection of page-specific
  styles.
- Primary actions, fields, tables, tabs, feedback, and navigation reuse shared
  contracts.
- Styling stays colocated as readable utility strings when Tailwind or another
  utility engine is available. Prefer standard scale utilities and configured
  semantic names such as `bg-primary`, `bg-surface`, `text-muted`, and `p-3`.
- Configure reusable colors, dimensions, radii, and breakpoints once. Do not
  repeat arbitrary-value utilities in component markup.
- Desktop/Mobile and Light/Dark share markup unless behavior genuinely differs.
- Use Lucide icons through the host project's normal integration.
- Attemptable actions remain enabled and explain unmet conditions with Toast
  feedback instead of failing silently.
- Search, filters, sorting, selection, pagination, forms, and navigation work
  when present.
- Accessibility and reduced motion are part of completion, not optional polish.

## Completion report

Report screens and shared components affected, responsive/theme states checked,
interactions exercised, commands run, and unresolved product or integration
gaps. A static render alone is not completion.
