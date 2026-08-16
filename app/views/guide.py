import flet as ft

from app.components.common import build_card, build_page_header
from app.theme import COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY

_GUIDE_SECTIONS = [
    (
        "ระบบนี้คืออะไร",
        [
            "ระบบยืม-คืนครุภัณฑ์ของสาขาวิทยาการคอมพิวเตอร์ ใช้ติดตามการยืม การคืน กำหนดวันคืน และการแจ้งอุปกรณ์หาย",
        ],
    ),
    (
        "ดูอุปกรณ์และสถานะ",
        [
            "หน้า อุปกรณ์ แสดงรายการครุภัณฑ์พร้อมสถานะปัจจุบัน: พร้อมใช้งาน / ถูกยืม / กำลังบำรุงรักษา / แจ้งหาย",
        ],
    ),
    (
        "ทำรายการยืมและคืน (สำหรับเจ้าหน้าที่)",
        [
            "เจ้าหน้าที่บันทึกรายการยืมโดยเลือกผู้ยืมและอุปกรณ์ พร้อมกำหนดวันครบกำหนดคืน",
            "การคืนอุปกรณ์ทำผ่านหน้า คืนอุปกรณ์ โดยเลือกผลลัพธ์การคืน เช่น คืนตามสภาพสมบูรณ์ หรือส่งซ่อมบำรุง",
        ],
    ),
    (
        "หน้า ของฉัน (สำหรับผู้ยืม)",
        [
            "เมื่อล็อกอินแล้ว ผู้ยืมสามารถดูรายการยืมของตัวเอง สถานะ และวันครบกำหนดคืนได้ที่หน้า ของฉัน",
        ],
    ),
    (
        "แจ้งอุปกรณ์หาย",
        [
            "เลือกอุปกรณ์ที่กำลังยืมอยู่ กรอกรายละเอียดวันที่หาย สถานที่ และคำอธิบาย แล้วส่งให้เจ้าหน้าที่ตรวจสอบ",
        ],
    ),
    (
        "คำถามที่พบบ่อย",
        [
            "ยืมอุปกรณ์ได้เมื่อใด — ยืมได้เมื่อเจ้าหน้าที่บันทึกรายการยืมและอุปกรณ์อยู่ในสถานะพร้อมใช้งาน",
            "คืนช้าเกินกำหนดทำอย่างไร — ติดต่อเจ้าหน้าที่สาขาโดยเร็วที่สุดเพื่อขยายกำหนดหรือคืนอุปกรณ์ทันที",
            "ลืมรหัสผ่านทำอย่างไร — ติดต่อเจ้าหน้าที่เพื่อขอรีเซ็ตรหัสผ่าน",
            "มีปัญหาอื่นติดต่อใคร — ติดต่อเจ้าหน้าที่สาขาได้ที่หน้า ติดต่อเจ้าหน้าที่",
        ],
    ),
]


def _guide_section(title: str, paragraphs: list[str]) -> ft.Container:
    return build_card(
        content=ft.Column(
            controls=[
                ft.Text(
                    title,
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=COLOR_TEXT_PRIMARY,
                ),
                *[
                    ft.Text(paragraph, size=13, color=COLOR_TEXT_SECONDARY)
                    for paragraph in paragraphs
                ],
            ],
            spacing=8,
            tight=True,
        ),
        padding=20,
    )


def build_guide_view(*, mobile: bool = False) -> ft.Container:
    """Static usage guide; the same scrollable column works on both breakpoints."""
    container = ft.Container(expand=True, padding=0)
    header = build_page_header(
        title="คู่มือการใช้งาน",
        subtitle="วิธีใช้งานระบบยืม-คืนครุภัณฑ์ BRU-CS",
        icon=ft.Icons.MENU_BOOK_OUTLINED,
    )
    container.content = ft.Column(
        controls=[
            header,
            *[
                _guide_section(title, paragraphs)
                for title, paragraphs in _GUIDE_SECTIONS
            ],
        ],
        spacing=16,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    return container
