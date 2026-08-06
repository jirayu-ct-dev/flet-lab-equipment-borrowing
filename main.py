import flet as ft


APP_TITLE = "Lab Equipment Borrowing"


def build_home() -> ft.Control:
    return ft.SafeArea(
        ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.SCIENCE_OUTLINED, size=64, color=ft.Colors.BLUE_700),
                    ft.Text(
                        APP_TITLE,
                        size=32,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Flet Web foundation is running.",
                        size=16,
                        color=ft.Colors.GREY_700,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
                tight=True,
            ),
            alignment=ft.Alignment.CENTER,
            expand=True,
            padding=24,
        ),
        expand=True,
    )


def main(page: ft.Page) -> None:
    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.add(build_home())


if __name__ == "__main__":
    ft.run(main)
