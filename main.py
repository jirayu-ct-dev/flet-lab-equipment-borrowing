import flet as ft

from app.env import load_env_file
from app.ui import AppUI, CANVAS, PRIMARY


def main(page: ft.Page) -> None:
    load_env_file()
    page.title = "ระบบยืม–คืนอุปกรณ์"
    page.padding = 0
    page.bgcolor = CANVAS
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=PRIMARY, font_family="Noto Sans Thai")
    AppUI(page)


if __name__ == "__main__":
    ft.run(main)
