# Component and Screen Patterns

Use these contracts to produce a coherent application. Implement only the
patterns required by the task, but keep their visual and behavioral contracts
consistent across screens.

## Contents

- Application shell and page surfaces
- Dashboard and data-list screens
- Forms and account screens
- Authentication
- Status and feedback
- Verification

## Application shell

Compose the shell from Sidebar, Navbar, main content, Toast viewport, and a skip
link.

- Desktop: 279px expanded sidebar, 80px collapsed sidebar, 88px navbar.
- Below 1024px: replace the fixed sidebar with an off-canvas drawer and use the
  compact navbar arrangement.
- Put the sidebar-collapse control in the navbar. Keep theme switching beside
  notification controls.
- Navigation is route-aware. Active items use a soft fill and clear text/icon
  contrast, never a decorative side stripe.
- Keep the user avatar circular. Icon badges color only the count, not the icon.
- Close drawers with Escape, overlay click, route change, or explicit close.
  Restore focus to the opener.

## Page header and surfaces

- PageHeader contains optional breadcrumbs, title, supporting context, and one
  upper-right primary action.
- Upper-right Add/New actions share the same blue background, 44px height,
  12px radius, and normal label weight across routes.
- Main content uses 32px desktop horizontal padding and 20px mobile padding.
- Group related content in 24px-radius bordered surfaces. Prefer alignment and
  whitespace over extra dividers and nested cards.

## Dashboard

Use a clear sequence: page heading, compact summary cards, primary data or
chart surface, then recent activity/table content. Keep metric labels muted,
values dominant, and comparisons secondary. Avoid decorative charts when real
data is unavailable; use a meaningful empty state.

## Data-list screens

Compose CategoryTabs when useful, then TableToolbar, EntityTable, selection
feedback, and Pagination inside one surface.

- Search belongs on the left; Filter and Export belong on the right.
- Search and Filter immediately affect displayed rows when they map to data.
- Sortable columns cycle default → descending → ascending → default and expose
  `aria-sort` plus a label describing the next action.
- Select-all affects visible rows. Individual selection reveals a selection bar
  with count, Clear, and relevant bulk actions.
- Row and bulk deletion provide Undo. Confirm server-side destructive actions
  when they cannot be safely reversed.
- Row actions stay aligned and compact: View, Edit, Delete or the subset the
  product supports. Connect routes when present; otherwise show an explanatory
  info Toast.
- Pagination uses the real data contract. If a prototype has no paging
  integration, keep the control attemptable and explain the limitation.
- Provide loading skeletons, a useful empty state, and an error state with a
  retry action.

At 600px and below, turn standard tables into concise row cards: selection and
identity remain visible, a labelled chevron expands secondary fields, and
actions appear with expanded details. A compact dashboard table may remain a
scrollable table when that preserves comprehension better.

## Forms

- Use a consistent FormField contract for label, optional hint, control, and
  inline error. Labels are clear; required state is announced in text or
  accessible metadata, not color alone.
- Controls are neutral semantic surfaces, at least 52px high, 12px radius, and
  aligned to a predictable grid.
- Desktop may use two columns for related short fields. Stack at 600px and
  below. Long text, uploaders, and address blocks span full width.
- Validate on submit and after a field has been touched; preserve entered data.
- Use Toast for submission outcome and inline messages for field-specific
  corrections. Move focus to the first invalid field or error summary.
- Edit forms initialize from real data and distinguish saving, success, error,
  and unsaved-change states.

## Account screens

Profile and Security use the same centered maximum content width and shared tab
treatment. Contact fields use normal input surfaces in both themes. Use circular
profile imagery; reserve rounded rectangles for document or product previews.
Keep the active Dark tab subdued rather than bright or glowing.

## Authentication

Desktop uses a 50:50 split: visual/product-value panel on the left and the form
on the right. Mobile shows the focused form experience and removes nonessential
visual content. Sign In and Sign Up reuse one responsive shell and field
contracts. Social actions use the provider's authentic mark with comfortable
icon-to-label spacing. Include password visibility, useful validation, and
clear navigation between authentication routes.

## Status and feedback

StatusChip is compact, rounded, and uses success, warning, danger, info, or
neutral tone without relying on color alone. Toast is an application primitive:

- warning for an unmet condition or validation summary;
- success for a completed create, update, delete, restore, or save;
- info for an unavailable integration or prototype limitation;
- error for a failed operation with a useful next step.

Stack multiple Toasts, make each dismissible, announce them appropriately, and
keep them clear of mobile navigation and safe-area insets.

## Verification matrix

For broad shared work, check every affected route at 1440px Light/Dark and
430px Light/Dark. Check component transitions at 600/601px and shell transitions
at 1023/1024px. Exercise every visible control with mouse and keyboard, reduced
motion, long content, empty data, loading, error, and success paths.
