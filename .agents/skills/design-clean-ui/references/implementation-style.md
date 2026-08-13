# Implementation Style

## Contents

- Utility-first styling
- Components, variants, and state
- Tokens, themes, icons, and assets
- Interaction behavior
- Editing discipline

## Utility-first styling

When the host uses Tailwind, treat “inline CSS” as complete utilities colocated
in component markup:

```html
<div class="flex items-center gap-3 rounded-xl border border-border p-3">
  Hello, World!
</div>
```

Do not translate this into a semantic class backed by a separate stylesheet.
Do not add component style blocks, CSS modules, or `@apply` in a Tailwind
project. Keep global CSS limited to fonts, semantic theme variables, focus,
reduced motion, and unavoidable browser foundations.

If the host has no utility engine, follow the styling adapter in
[project-integration.md](project-integration.md); do not force Tailwind into the
project without authorization.

Prefer utilities in this order:

1. standard Tailwind scale: `p-3`, `pt-5`, `pb-7`, `gap-3`, `rounded-xl`;
2. configured semantic token: `bg-primary`, `bg-surface`, `text-muted`,
   `border-border`, `w-sidebar`, `rounded-card`;
3. an arbitrary value only for an unavoidable one-off browser calculation or
   third-party integration value that cannot be represented by configuration.

For example, replace a CSS-variable background utility with `bg-surface`.
Express 20px top and 28px bottom padding as `pt-5 pb-7`. If the same exact
custom dimension appears more than once, name it in configuration instead of
repeating raw values.

Do not use arbitrary values for ordinary colors, spacing, sizes, radii, or
breakpoints. If an exception is unavoidable, keep it isolated and explain why
a standard utility or named token cannot represent it.

Avoid deeply nested arbitrary selector utilities. Prefer a component prop,
direct class binding, named variant, or small markup adjustment that remains
easy to scan.

## Component conventions

- Match the host framework. In Vue prefer `<script setup>`; in React use focused
  function components; elsewhere use the native component model.
- Use arrow functions for handlers and helpers where the language permits.
- Keep component inputs and events explicit, typed when the project uses types.
- Use framework state primitives rather than direct DOM mutation.
- Keep page composition in routes/pages and reusable behavior in components or
  focused hooks/composables.
- Prefer one responsive component tree to duplicated Desktop/Mobile markup.

## Variants and state

Use complete static utility strings so the compiler can discover them:

```js
const toneClasses = {
  success: 'bg-success/15 text-success',
  warning: 'bg-warning/15 text-warning',
}
```

Do not construct utility names such as `` `bg-${tone}-500` ``. Use the host
framework's class binding for discrete state. Use descriptive `data-*` hooks
when descendant selectors must react to parent state.

## Tokens and themes

- Prefer semantic utilities such as `bg-surface`, `text-content`, `text-muted`,
  and `border-border` when the host exposes them.
- Configure missing semantic aliases before writing raw CSS-variable or hex
  arbitrary utilities in markup.
- Bind theme state at the application or standalone-screen root.
- Initialize and persist theme through the host's normal state mechanism.
- Do not fork page markup for Dark mode.
- Map existing brand tokens to the nearest semantic role instead of overwriting
  a sound host design system.

## Components

- Reuse or create only the required shell, navigation, page header, buttons,
  fields, chips, toolbar, table, pagination, cards, tabs, uploader, dialog, and
  Toast patterns.
- Abstract after two real uses or when one complex contract clearly benefits.
- Preserve dimensions, state behavior, and responsive behavior when refactoring.
- Do not create page-specific variants when a prop or composition slot expresses
  the genuine difference cleanly.

## Icons and assets

- Use Lucide through the host project's icon package or adapter. In Nuxt,
  Nuxt Icon with `lucide:*` is preferred when already available.
- Size icons explicitly, keep them from shrinking, and inherit semantic color.
- Use host-provided assets and branding. Never copy names or imagery from an
  authoring example into another product unless explicitly requested.
- Preserve image aspect ratio and meaningful alternative text; use empty alt
  text for decorative images.

## Interaction behavior

- Keep controls enabled when users can reasonably attempt the action.
- When a prerequisite or integration is missing, show a Toast stating what is
  unavailable and what is needed.
- Use warning for validation, success for completion, info for unavailable
  integration, and error for failure.
- Provide accessible names for icon-only controls and live announcements for
  feedback.
- Implement sorting, expansion, selection, bulk actions, Undo, pagination,
  validation, navigation, and theme/sidebar persistence when present.
- Visible Search and Filter controls must affect displayed data.
- Use the target's real paging contract. Without one, explain the prototype
  limitation rather than inventing fake client/server behavior.
- Support loading, empty, error, success, long-content, and permission states
  appropriate to the feature.

## Editing discipline

- Read host instructions, the closest existing component, and the applicable
  bundled pattern before creating a new convention.
- Change only the requested surface and the foundations it truly requires.
- Remove obsolete classes, imports, assets, and state introduced by the change.
- Do not mix a style-system refactor with an unrelated visual redesign.
