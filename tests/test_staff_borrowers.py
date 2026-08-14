import flet as ft

from app.services.fake_services import FakeInventoryService
from app.views.staff_borrowers import StaffBorrowersView


def test_staff_and_borrower_service_support_lookup_and_status() -> None:
    service = FakeInventoryService()

    staff = service.create_staff("ST-999", "Ada", status="active")
    borrower = service.create_borrower("BR-999", "Lin", status="active")

    assert staff.staff_code == "ST-999"
    assert borrower.borrower_code == "BR-999"
    assert service.get_staff("ST-999").status == "active"
    assert service.get_borrower("BR-999").status == "active"
    assert service.list_staff(include_inactive=True)
    assert service.list_borrowers(include_inactive=True)


class RejectingPeopleService(FakeInventoryService):
    def create_staff(self, *args, **kwargs):
        return None

    def create_borrower(self, *args, **kwargs):
        return None


def test_staff_form_keeps_values_when_save_fails() -> None:
    view = StaffBorrowersView(RejectingPeopleService())
    view._open_new_staff(None)
    view.staff_code.value = "ST-FAIL"
    view.staff_name.value = "ทดสอบ"

    view._handle_save_staff(None)

    assert "ไม่สำเร็จ" in view.feedback.value
    assert view.staff_code.value == "ST-FAIL"
    assert view.staff_name.value == "ทดสอบ"
    assert view.staff_dialog.open is True


def test_borrower_form_keeps_values_when_save_fails() -> None:
    view = StaffBorrowersView(RejectingPeopleService())
    view._open_new_borrower(None)
    view.borrower_code.value = "BR-FAIL"
    view.borrower_name.value = "ทดสอบ"

    view._handle_save_borrower(None)

    assert "ไม่สำเร็จ" in view.feedback.value
    assert view.borrower_code.value == "BR-FAIL"
    assert view.borrower_name.value == "ทดสอบ"
    assert view.borrower_dialog.open is True


def test_people_add_buttons_open_the_matching_dialog() -> None:
    view = StaffBorrowersView(FakeInventoryService())

    view._open_new_staff(None)
    assert view.staff_dialog.open is True

    view.staff_dialog.open = False
    view._open_new_borrower(None)
    assert view.borrower_dialog.open is True


def test_people_lists_render_as_tables() -> None:
    view = StaffBorrowersView(FakeInventoryService())

    staff_table = view.staff_container.content.content.controls[0]
    assert isinstance(staff_table, ft.DataTable)
    assert len(staff_table.columns) == 5

    view._switch_to_borrowers(None)
    borrower_table = view.borrower_container.content.content.controls[0]
    assert isinstance(borrower_table, ft.DataTable)
    assert len(borrower_table.columns) == 6


def test_people_search_toolbars_keep_search_reset_and_add_together() -> None:
    view = StaffBorrowersView(FakeInventoryService())

    staff_toolbar = view.mode_container.content.controls[0].content.controls[0]
    assert isinstance(staff_toolbar, ft.ResponsiveRow)
    assert staff_toolbar.controls[0].content is view.staff_search
    staff_actions = staff_toolbar.controls[1].content.controls
    assert staff_actions[0].content == "เพิ่มผู้บันทึกรายการ"
    assert staff_actions[1].content == "รีเซ็ต"
    assert view.staff_search.border_radius == 12
    assert staff_actions[1].style.shape.radius == 12

    view._switch_to_borrowers(None)
    borrower_toolbar = view.mode_container.content.controls[0].content.controls[0]
    assert borrower_toolbar.controls[0].content is view.borrower_search
    borrower_actions = borrower_toolbar.controls[1].content.controls
    assert borrower_actions[0].content == "เพิ่มผู้ยืม"
    assert borrower_actions[1].content == "รีเซ็ต"
