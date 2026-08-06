import flet as ft


def build_state_view(title: str, message: str, *, icon: str | None = None) -> ft.Container:
    content = [
        ft.Icon(icon or ft.Icons.INFO_OUTLINE, size=42, color=ft.Colors.BLUE_600),
        ft.Text(title, size=20, weight=ft.FontWeight.W_600),
        ft.Text(message, size=14, color=ft.Colors.GREY_700),
    ]

    return ft.Container(
        content=ft.Column(
            controls=content,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
            tight=True,
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
        padding=24,
    )
