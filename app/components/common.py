from typing import Callable, Any
import flet as ft
from app.theme import STATUS_THEMES, COLOR_BORDER, COLOR_SURFACE, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, MOBILE_BREAKPOINT


def update_control(control: ft.Control) -> None:
    """Update a mounted control; allow view-model tests to run before mounting."""
    try:
        control.update()
    except RuntimeError as error:
        if "Control must be added to the page first" not in str(error):
            raise


def open_dialog(owner: ft.Control, dialog: ft.AlertDialog) -> None:
    """Open a dialog both on a mounted page and in view-model tests."""
    try:
        page = owner.page
    except RuntimeError:
        page = None
    if page is not None:
        page.show_dialog(dialog)
    else:
        dialog.open = True


def close_dialog(owner: ft.Control, dialog: ft.AlertDialog) -> None:
    """Close the active dialog without requiring the owner to be mounted."""
    try:
        page = owner.page
    except RuntimeError:
        page = None
    if page is not None and dialog.open:
        page.pop_dialog()
    else:
        dialog.open = False


def build_form_dialog(
    *,
    title: str,
    icon: str,
    content: ft.Control,
    save_label: str,
    on_save: Callable[[ft.ControlEvent], None],
    on_cancel: Callable[[ft.ControlEvent], None],
) -> ft.AlertDialog:
    return ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Icon(icon, color=ft.Colors.BLUE_600, size=22),
                ft.Text(title, size=18, weight=ft.FontWeight.W_600),
            ],
            spacing=10,
        ),
        content=ft.Container(content=content, width=600),
        actions=[
            ft.TextButton("ยกเลิก", on_click=on_cancel),
            ft.Button(
                save_label,
                icon=ft.Icons.SAVE,
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
                on_click=on_save,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=20),
        scrollable=True,
    )


def build_status_chip(status: str, custom_label: str | None = None) -> ft.Container:
    theme_info = STATUS_THEMES.get(
        status.lower(),
        {
            "text": custom_label or status.title(),
            "color": ft.Colors.BLUE_700,
            "bgcolor": ft.Colors.BLUE_50,
            "icon": ft.Icons.INFO_OUTLINE,
        },
    )

    label_text = custom_label or theme_info["text"]

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(theme_info["icon"], size=14, color=theme_info["color"]),
                ft.Text(
                    label_text,
                    size=12,
                    weight=ft.FontWeight.W_600,
                    color=theme_info["color"],
                ),
            ],
            spacing=4,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=theme_info["bgcolor"],
        padding=ft.Padding(left=10, top=4, right=10, bottom=4),
        border_radius=16,
        border=ft.Border.all(1, theme_info["color"]),
    )


def build_data_card(
    *,
    title: str,
    icon: str | None = None,
    status: tuple[str, str] | None = None,
    fields: list[tuple[str, str]] | None = None,
    actions: list[ft.Control] | None = None,
    header_actions: list[ft.Control] | None = None,
    full_width_fields: list[str] | None = None,
) -> ft.Container:
    """Record card used on mobile in place of a DataTable row."""
    header_controls: list[ft.Control] = []
    if icon is not None:
        header_controls.append(ft.Icon(icon, size=18, color=ft.Colors.BLUE_600))
    header_controls.append(
        ft.Text(
            title,
            size=15,
            weight=ft.FontWeight.BOLD,
            color=COLOR_TEXT_PRIMARY,
            expand=True,
        )
    )
    if status is not None:
        header_controls.append(build_status_chip(status[0], status[1]))
    header_controls.extend(header_actions or [])

    rows: list[ft.Control] = [
        ft.Row(
            controls=header_controls,
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
    ]

    def build_cell(label: str, value: str) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Text(label, size=11, color=COLOR_TEXT_SECONDARY),
                ft.Text(
                    value or "-",
                    size=14,
                    weight=ft.FontWeight.W_500,
                    color=COLOR_TEXT_PRIMARY,
                ),
            ],
            spacing=2,
            tight=True,
        )

    def build_pair_row(pair: list[ft.Control]) -> ft.Row:
        return ft.Row(
            controls=[ft.Container(content=cell, expand=True) for cell in pair],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    full_width = set(full_width_fields or [])
    pair: list[ft.Control] = []
    for label, value in fields or []:
        cell = build_cell(label, value)
        if label in full_width:
            if pair:
                rows.append(build_pair_row(pair))
                pair = []
            rows.append(cell)
        else:
            pair.append(cell)
            if len(pair) == 2:
                rows.append(build_pair_row(pair))
                pair = []
    if pair:
        rows.append(build_pair_row(pair))

    if actions:
        rows.append(ft.Divider(height=1, thickness=1, color=COLOR_BORDER))
        rows.append(
            ft.Row(
                controls=actions,
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    return build_card(content=ft.Column(controls=rows, spacing=10), padding=16)


def build_card_list(controls: list[ft.Control]) -> ft.Column:
    """Stack record cards vertically for mobile list views."""
    return ft.Column(
        controls=controls,
        spacing=12,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )


def handle_mobile_resize(
    view: ft.Control,
    rerender: Callable[[], None],
    e: ft.LayoutSizeChangeEvent,
) -> None:
    """Flip a view's table/card rendering when width crosses the mobile breakpoint."""
    mobile = e.width <= MOBILE_BREAKPOINT
    if mobile != view.mobile:
        view.mobile = mobile
        rerender()
        update_control(view)


def build_card(
    content: ft.Control,
    *,
    padding: int | ft.Padding = 16,
    on_click: Callable[[ft.ControlEvent], None] | None = None,
    width: int | float | None = None,
    border_color: str | None = None,
    bgcolor: str = COLOR_SURFACE,
) -> ft.Container:

    card = ft.Container(
        content=content,
        padding=padding if isinstance(padding, ft.Padding) else ft.Padding(left=padding, top=padding, right=padding, bottom=padding),
        width=width,
        bgcolor=bgcolor,
        border_radius=24,
        border=ft.Border.all(1, border_color or COLOR_BORDER),
        animate=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
    )

    if on_click is not None:
        card.on_click = on_click
        card.mouse_cursor = ft.MouseCursor.CLICK

        def on_hover(e: ft.ControlEvent) -> None:
            if e.data == "true":
                card.border = ft.Border.all(1, ft.Colors.BLUE_400)
            else:
                card.border = ft.Border.all(1, border_color or COLOR_BORDER)
            card.update()

        card.on_hover = on_hover

    return card


def build_filter_bar(
    *,
    search_control: ft.Control | None,
    action_controls: list[ft.Control],
    footer: ft.Control | None = None,
    search_col: int | float = 5,
) -> ft.Container:
    """Build the shared search-left, filters-right toolbar used by list pages."""
    toolbar_controls: list[ft.Control] = []
    if search_control is not None:
        toolbar_controls.append(
            ft.Container(
                content=search_control,
                col={"xs": 12, "md": search_col},
            )
        )
    toolbar_controls.append(
        ft.Container(
            content=ft.Row(
                controls=action_controls,
                spacing=12,
                run_spacing=12,
                wrap=True,
                alignment=ft.MainAxisAlignment.END,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            col={"xs": 12, "md": 12 - search_col if search_control is not None else 12},
            alignment=ft.Alignment.CENTER_RIGHT,
        )
    )
    toolbar = ft.ResponsiveRow(
        controls=toolbar_controls,
        spacing=16,
        run_spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    controls: list[ft.Control] = [toolbar]
    if footer is not None:
        controls.append(
            ft.Row(
                controls=[ft.Container(expand=True), footer],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
    return build_card(
        content=ft.Column(controls=controls, spacing=10),
        padding=16,
    )


def build_table_surface(
    table: ft.DataTable,
    *,
    table_width: int = 1000,
    initial_width: float | None = None,
) -> ft.Container:
    """Show a consistent full-width table surface with mobile horizontal scroll.

    ``initial_width`` is the last known rendered width of the surface (e.g. from
    the owning view's resize handler). It lets a freshly rebuilt table keep its
    responsive full-width layout immediately, instead of waiting for an
    ``on_size_change`` event that does not re-fire when a same-size surface
    replaces another one.
    """
    table.width = (
        max(initial_width - 24, table_width)
        if initial_width is not None
        else table_width
    )
    surface = build_card(
        ft.Row(
            controls=[table],
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=12,
    )
    surface.width = float("inf")

    def handle_size(e: ft.LayoutSizeChangeEvent) -> None:
        table.width = max(e.width - 24, table_width)
        update_control(table)

    surface.on_size_change = handle_size
    return surface


def build_page_header(
    title: str,
    subtitle: str,
    *,
    icon: str | None = None,
    action_control: ft.Control | None = None,
) -> ft.Container:
    header_left = ft.Row(
        controls=[
            *(
                [
                    ft.Container(
                        content=ft.Icon(icon, size=24, color=ft.Colors.BLUE_600),
                        padding=10,
                        border_radius=10,
                        bgcolor=ft.Colors.BLUE_50,
                    )
                ]
                if icon
                else []
            ),
            ft.Column(
                controls=[
                    ft.Text(title, size=22, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                    ft.Text(subtitle, size=13, color=COLOR_TEXT_SECONDARY),
                ],
                spacing=2,
                tight=True,
            ),
        ],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    if action_control is not None:
        content = ft.Row(
            controls=[header_left, action_control],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
            run_spacing=12,
        )
    else:
        content = header_left

    return ft.Container(
        content=content,
        padding=ft.Padding(left=0, top=0, right=0, bottom=16),
    )


def build_alert_banner(message: str, banner_type: str = "info") -> ft.Container:
    type_configs = {
        "success": {
            "bgcolor": ft.Colors.GREEN_50,
            "border": ft.Colors.GREEN_300,
            "text_color": ft.Colors.GREEN_900,
            "icon": ft.Icons.CHECK_CIRCLE,
            "icon_color": ft.Colors.GREEN_600,
        },
        "error": {
            "bgcolor": ft.Colors.RED_50,
            "border": ft.Colors.RED_300,
            "text_color": ft.Colors.RED_900,
            "icon": ft.Icons.ERROR,
            "icon_color": ft.Colors.RED_600,
        },
        "warning": {
            "bgcolor": ft.Colors.AMBER_50,
            "border": ft.Colors.AMBER_300,
            "text_color": ft.Colors.AMBER_900,
            "icon": ft.Icons.WARNING,
            "icon_color": ft.Colors.AMBER_600,
        },
        "info": {
            "bgcolor": ft.Colors.BLUE_50,
            "border": ft.Colors.BLUE_300,
            "text_color": ft.Colors.BLUE_900,
            "icon": ft.Icons.INFO,
            "icon_color": ft.Colors.BLUE_600,
        },
    }

    config = type_configs.get(banner_type, type_configs["info"])

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(config["icon"], color=config["icon_color"], size=18),
                ft.Text(message, size=13, color=config["text_color"], weight=ft.FontWeight.W_500, expand=True),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=config["bgcolor"],
        padding=ft.Padding(left=14, top=10, right=14, bottom=10),
        border_radius=8,
        border=ft.Border.all(1, config["border"]),
    )


def build_state_view(title: str, message: str, *, icon: str | None = None) -> ft.Container:
    content = [
        ft.Container(
            content=ft.Icon(icon or ft.Icons.INFO_OUTLINE, size=36, color=ft.Colors.BLUE_600),
            padding=16,
            border_radius=30,
            bgcolor=ft.Colors.BLUE_50,
        ),
        ft.Text(title, size=18, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY),
        ft.Text(message, size=13, color=COLOR_TEXT_SECONDARY, text_align=ft.TextAlign.CENTER),
    ]

    return ft.Container(
        content=ft.Column(
            controls=content,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
            tight=True,
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
        padding=32,
    )
