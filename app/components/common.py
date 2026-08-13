from typing import Callable, Any
import flet as ft
from app.theme import STATUS_THEMES, COLOR_BORDER, COLOR_SURFACE, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY


def update_control(control: ft.Control) -> None:
    """Update a mounted control; allow view-model tests to run before mounting."""
    try:
        control.update()
    except RuntimeError as error:
        if "Control must be added to the page first" not in str(error):
            raise


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
