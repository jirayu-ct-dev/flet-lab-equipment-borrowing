import flet as ft

from app.views.guide import build_guide_view

_GUIDE_SECTION_TITLES = [
    "ระบบนี้คืออะไร",
    "ดูอุปกรณ์และสถานะ",
    "ทำรายการยืมและคืน (สำหรับเจ้าหน้าที่)",
    "หน้า ของฉัน (สำหรับผู้ยืม)",
    "แจ้งอุปกรณ์หาย",
    "คำถามที่พบบ่อย",
]


def _section_titles(view: ft.Container) -> list[str]:
    column = view.content
    cards = column.controls[1:]
    return [card.content.controls[0].value for card in cards]


def test_guide_view_builds_with_header() -> None:
    view = build_guide_view()

    assert isinstance(view, ft.Container)
    assert view.expand is True
    column = view.content
    assert isinstance(column, ft.Column)
    header = column.controls[0]
    title = header.content.controls[1].controls[0]
    assert title.value == "คู่มือการใช้งาน"


def test_guide_view_contains_all_sections() -> None:
    view = build_guide_view()

    assert _section_titles(view) == _GUIDE_SECTION_TITLES


def test_guide_view_builds_on_mobile_without_service() -> None:
    view = build_guide_view(mobile=True)

    assert view.expand is True
    assert _section_titles(view) == _GUIDE_SECTION_TITLES
