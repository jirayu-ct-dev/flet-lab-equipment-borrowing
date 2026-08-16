import flet as ft

from app.services.fake_services import FakeInventoryService
from app.views.contact import ContactView


class EmptyStaffService(FakeInventoryService):
    def list_staff(self, *, include_inactive: bool = False):
        return []


def test_contact_view_renders_staff_table() -> None:
    view = ContactView(FakeInventoryService())

    surface = view.staff_container.content
    table = surface.content.controls[0]
    assert isinstance(table, ft.DataTable)
    assert [column.label.value for column in table.columns] == [
        "ชื่อ",
        "อีเมล",
        "โทรศัพท์",
    ]
    assert len(table.rows) == 1
    assert table.rows[0].cells[0].content.value == "Ada Lovelace"
    assert table.rows[0].cells[1].content.value == "ada@example.com"
    assert table.rows[0].cells[2].content.value == "-"


def test_contact_view_renders_cards_on_mobile() -> None:
    view = ContactView(FakeInventoryService(), mobile=True)

    content = view.staff_container.content
    assert isinstance(content, ft.Column)
    assert isinstance(content.controls[0], ft.Container)
    header = content.controls[0].content.controls[0]
    assert isinstance(header, ft.Row)
    assert header.controls[1].value == "Ada Lovelace"


def test_contact_view_empty_state() -> None:
    view = ContactView(EmptyStaffService())

    state = view.staff_container.content
    assert "ไม่พบข้อมูลเจ้าหน้าที่" in state.content.controls[1].value
    assert "ยังไม่มีข้อมูลเจ้าหน้าที่ในระบบ" in state.content.controls[2].value
