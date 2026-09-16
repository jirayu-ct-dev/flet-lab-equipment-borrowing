import os

import flet as ft

from app.env import load_env_file
from app.seed import seed_render_demo
from app.service import AppService
from app.ui import AppUI, CANVAS, PRIMARY


def main(page: ft.Page) -> None:
    load_env_file()
    service = AppService()
    if os.getenv("APP_SEED_RENDER_DEMO") == "1":
        seed_render_demo(service)
    page.title = "ระบบยืม–คืนอุปกรณ์"
    page.padding = 0
    page.bgcolor = CANVAS
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=PRIMARY, font_family="Noto Sans Thai")
    AppUI(page, service=service)


if __name__ == "__main__":
    ft.run(main)
