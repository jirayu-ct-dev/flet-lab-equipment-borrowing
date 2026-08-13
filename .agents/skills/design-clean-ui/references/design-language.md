# Design Language

This file is the portable visual specification. Use it without requiring this
source repository or an external design file. Preserve confirmed host-product
branding and requirements while mapping these semantic roles onto its existing
token system.

## Foundations

- Font: Plus Jakarta Sans when the host has no established product font.
- Base text: 14px with 1.5 line height.
- Primary: `#1a71f6`; primary strong: `#1154d4`.
- Canvas: `#f7f7f7` Light; `#101011` Dark.
- Surface: `#ffffff` Light; `#1a1a1b` Dark.
- Soft surface: `#f6f6f6` Light; `#242424` Dark.
- Text: `#323130` Light; `#f6f6f6` Dark.
- Muted text: `#737373` Light; `#b0b0b0` Dark.
- Border: `#d1d1d1` Light; `#3d3d3d` Dark.
- Active Dark navigation: translucent primary blue with `#8db8ff` content.

Use semantic variables or the host token mechanism. A minimal variable map may
use `--ui-primary`, `--ui-primary-strong`, `--ui-canvas`, `--ui-surface`,
`--ui-surface-soft`, `--ui-text`, `--ui-muted`, and `--ui-border`. Alias them
through the host utility configuration when available. Do not scatter theme
base colors through component markup when a token exists.

These hex values define token defaults, not component classes. Configure them
once, then consume readable utilities such as `bg-primary`, `bg-surface`,
`text-content`, `text-muted`, and `border-border`. Do not write raw color values
or CSS variables inside arbitrary-value utility brackets.

## Geometry

- Expanded sidebar: 279px; collapsed sidebar: 80px.
- Navbar: 88px high.
- Page content: 32px desktop horizontal padding; 20px mobile padding.
- Cards: 24px radius, 1px semantic border, surface background, no heavy shadow.
- Primary, form, toolbar, and navigation buttons: at least 44px high, commonly
  12px radius.
- Form controls: 52px minimum height, 12px radius, 14px horizontal padding.
- Compact toolbar controls: 44px high.
- Standard table rows: 72px; sortable header controls: 32px.
- Dense desktop table actions: 20px control/icon. Mobile table actions: 32px
  control with a 24px icon. Keep these compact exceptions labelled, keyboard
  reachable, and visibly focused.

## Responsive rules

- At 600px and below: stacked forms, mobile table cards, compact page padding,
  and hidden nonessential secondary content.
- At 601px: restore desktop table structure where applicable.
- At 1023px and below: off-canvas navigation drawer and compact navbar.
- At 1024px and above: desktop shell and optional collapsed sidebar.

Use explicit host-system breakpoint syntax. Do not substitute convenient
framework defaults because a breakpoint is nearby.

Register repeated exact dimensions and breakpoints with semantic names rather
than placing their pixel values in arbitrary utility brackets.

## Surface and hierarchy

- Prefer whitespace and alignment over decorative dividers.
- Use subtle borders and soft fills; avoid glossy gradients and large shadows.
- Keep page actions at the upper right of the heading.
- Keep table search on the left and Filter/Export on the right.
- Use blue for primary actions, links, and active navigation; reserve red for
  destructive actions and notification counts.
- Keep top-right action labels normal-weight.
- Use circular user avatars and compact status chips.
- Active states use a soft filled surface, never a decorative side stripe.
- Keep the number of visual emphasis levels small: page title, section title,
  body, muted metadata. Do not make every label bold.

## Theme behavior

Light and Dark share markup and geometry. Change semantic tokens and add scoped
variant colors only when a state needs distinct contrast. Status chips retain
explicit success, warning, danger, and info fills unless contrast requires a
Dark adjustment. Dark active tabs and navigation remain subdued, not glowing.

## Motion and accessibility

- Use 180ms transitions for drawer, collapse, rotation, opacity, and transform.
- Reduce animation and transition duration to 0.01ms for reduced motion.
- Maintain a visible 2px primary focus outline with 2px offset.
- Preserve 44px targets for primary, form, toolbar, and navigation controls;
  use the documented compact exception only inside dense data rows.
- Meet WCAG AA contrast, retain semantic markup, label icon-only controls, and
  do not rely on color alone for meaning.
