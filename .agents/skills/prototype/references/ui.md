# UI Prototypes

Use this mode when the open question is about layout, information hierarchy, interaction, density, or visual direction.

## Work in realistic context

Prefer mounting variants inside the existing page or shell so they encounter real navigation, content density, responsive constraints, and design tokens. Create a dedicated prototype route only when no meaningful host surface exists.

Reuse the project's component library and styling conventions. Preserve data loading above the variant boundary when safe; stub mutations and irreversible actions.

## Create meaningful alternatives

Default to three variants and use two to four unless the user requests otherwise. Each variant should differ structurally—for example in hierarchy, navigation, primary action, grouping, or interaction model—not merely in color or copy.

Name the variants by their idea, not only `A`, `B`, and `C`. Keep them independent enough that each can explore its premise without a shared layout forcing convergence.

## Make comparison easy

Provide one stable route or entry point and a lightweight switcher. A URL parameter such as `?variant=compact-table` is useful because the view can be reloaded and shared. If keyboard shortcuts are added, do not intercept keys while the user is typing in an input, textarea, select, or editable element.

For each variant, exercise representative states where relevant:

- normal populated content;
- loading or progressive disclosure;
- empty and error states;
- long labels or dense data;
- narrow and wide viewports;
- permission or disabled-action states without making controls inaccessible or silently hiding the reason.

Keep the switcher visually distinct and prevent prototype-only controls from appearing in production builds.

## Conclude

Ask for feedback about the underlying decisions: what information should lead, which action should dominate, what feels confusing, and which parts should be combined. Record the chosen direction and the reasons.

Rebuild the winning direction to production standards. Remove losing variants and prototype-only controls from the production path unless the user explicitly wants to retain them as design references.
