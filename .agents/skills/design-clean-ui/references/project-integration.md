# Project Integration

This skill must work when its folder is the only artifact copied into another
repository. Never assume the authoring demo, its routes, components, assets, or
configuration are present.

## Inspect before changing

Read the host repository's agent instructions and inspect:

- package manager, framework, rendering mode, routing, and build commands;
- utility/CSS system, token definitions, theme mechanism, icon package, and
  component library;
- existing shell, shared controls, data access, validation, notifications, and
  accessibility conventions;
- affected routes at desktop and mobile sizes before editing.

Reuse a sound existing convention. Do not replace an established framework or
component library merely to imitate the reference implementation.

## Decide how to integrate

Apply this order:

1. Preserve host product requirements, routes, content, brand, and data.
2. Reuse compatible host primitives and map their variants to this skill's
   visual/behavioral contracts.
3. Add only the missing semantic tokens and shared primitives needed by the
   requested scope.
4. Introduce a dependency only when it provides clear reusable value, is
   allowed by repository policy, and cannot be achieved cleanly with the
   existing stack.

When host conventions conflict with this skill, preserve behavior and
accessibility first, then translate the clean visual language rather than
forcing a rewrite.

## Styling adapter

- Tailwind present: use standard utilities directly in markup and static class
  maps. Extend semantic tokens through the project's normal Tailwind setup so
  markup uses names such as `bg-primary`, `bg-surface`, `text-content`,
  `border-border`, `w-sidebar`, and `rounded-card`.
- Another utility engine present: use its equivalent complete utility strings
  and breakpoint syntax.
- No utility engine: preserve the host styling architecture. Do not silently
  install Tailwind. Implement semantic tokens and colocated/component-scoped
  styling with the smallest compatible change, and disclose the deviation.

The desired outcome is consistent colocated styling, not a forced dependency.

## Token configuration

Prefer the framework's supported configuration surface over arbitrary values in
markup. In a Nuxt UI project, define palette roles in `app.config.ts`:

```ts
export default defineAppConfig({
  ui: {
    colors: {
      primary: 'sky',
      secondary: 'blue',
      success: 'emerald',
      info: 'cyan',
      warning: 'amber',
      error: 'rose',
      neutral: 'slate',
    },
  },
})
```

Then use readable classes such as `bg-primary`, `text-error`, and
`border-border`. Define product roles that are not supplied by the UI library
through the installed Tailwind version's normal theme configuration:

```js
colors: {
  surface: 'var(--ui-surface)',
  content: 'var(--ui-text)',
  muted: 'var(--ui-muted)',
  border: 'var(--ui-border)',
}
```

Give repeated dimensions and breakpoints meaningful names as well, for example
`sidebar`, `navbar`, `page`, `card`, `mobile`, and `shell`. This allows
`w-sidebar`, `h-navbar`, `px-page`, `rounded-card`, and named responsive
variants instead of repeating raw measurements.

When the host already defines comparable roles, reuse its names rather than
creating duplicate aliases. Adapt configuration syntax to the installed
Tailwind/Nuxt UI version.

## Framework adapter

- Vue/Nuxt: prefer `<script setup>`, Composition API, arrow-function handlers,
  explicit props/emits, and Nuxt Icon with Lucide when available.
- React/Next: use focused function components, arrow-function handlers, props
  with clear types where TypeScript exists, and the host Lucide package.
- Svelte/SvelteKit or other component frameworks: follow native component and
  state conventions while preserving the same tokens, contracts, and behavior.

Do not port framework-specific syntax into an incompatible project.

## Foundation sequence

For a project without a usable UI foundation, establish only what the requested
screens need, in this order:

1. semantic Light/Dark tokens and typography;
2. focus and reduced-motion foundations;
3. Button, IconButton, Input/FormField, StatusChip, and Toast;
4. shell/navigation when the scope includes authenticated pages;
5. table, pagination, tabs, cards, uploaders, or dialogs as required;
6. page composition and route integration.

Avoid speculative components. Generalize after a second real use or when a
single complex contract clearly benefits from isolation.

## Product-state checklist

For every feature surface identify default, hover, focus, active, loading,
empty, error, success, disabled-by-platform, and reduced-motion behavior as
applicable. A control may be disabled only when the platform prevents an
attempt or activating it would be harmful; otherwise keep it enabled and
explain unmet conditions through feedback.

## Handoff

State which host conventions were reused, which tokens/components were added,
and any deviation caused by framework or dependency constraints. Never claim
pixel fidelity to a source that was not available; claim compliance with this
bundled system and the verified host behavior.
