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


def test_people_lists_render_as_cards_on_mobile() -> None:
    view = StaffBorrowersView(FakeInventoryService(), mobile=True)

    staff_cards = view.staff_container.content
    assert isinstance(staff_cards, ft.Column)
    assert all(isinstance(card, ft.Container) for card in staff_cards.controls)

    view._switch_to_borrowers(None)
    borrower_cards = view.borrower_container.content
    assert isinstance(borrower_cards, ft.Column)
    assert all(isinstance(card, ft.Container) for card in borrower_cards.controls)


def test_people_mobile_cards_put_edit_in_header_and_email_on_own_row() -> None:
    view = StaffBorrowersView(FakeInventoryService(), mobile=True)

    staff_rows = view.staff_container.content.controls[0].content.controls
    staff_header = staff_rows[0]
    assert isinstance(staff_header, ft.Row)
    edit_button = staff_header.controls[-1]
    assert isinstance(edit_button, ft.IconButton)
    assert edit_button.tooltip == "แก้ไขผู้บันทึกรายการ"
    staff_email_row = staff_rows[-1]
    assert isinstance(staff_email_row, ft.Column)
    assert staff_email_row.controls[0].value == "อีเมล"

    view._switch_to_borrowers(None)
    borrower_rows = view.borrower_container.content.controls[0].content.controls
    borrower_header = borrower_rows[0]
    edit_button = borrower_header.controls[-1]
    assert isinstance(edit_button, ft.IconButton)
    assert edit_button.tooltip == "แก้ไขผู้ยืม"
    borrower_email_row = borrower_rows[-1]
    assert isinstance(borrower_email_row, ft.Column)
    assert borrower_email_row.controls[0].value == "อีเมล"


def test_people_reset_keeps_table_responsive_width() -> None:
    view = StaffBorrowersView(FakeInventoryService())
    view._handle_resize(type("Size", (), {"width": 1600})())

    view._handle_staff_reset(None)
    staff_table = view.staff_container.content.content.controls[0]
    assert staff_table.width == 1576

    view._switch_to_borrowers(None)
    view._handle_borrower_reset(None)
    borrower_table = view.borrower_container.content.content.controls[0]
    assert borrower_table.width == 1576


def test_people_search_toolbars_keep_search_reset_and_add_together() -> None:
    view = StaffBorrowersView(FakeInventoryService())

    staff_toolbar = view.mode_container.content.controls[0].content.controls[0]
    assert isinstance(staff_toolbar, ft.ResponsiveRow)
    assert staff_toolbar.controls[0].content is view.staff_search
    staff_actions = staff_toolbar.controls[1].content.controls
    assert staff_actions[0].content == "เพิ่มผู้บันทึกรายการ"
    assert staff_actions[1].content == "รีเฟรช"
    assert view.staff_search.border_radius == 12
    assert staff_actions[1].style.shape.radius == 12

    view._switch_to_borrowers(None)
    borrower_toolbar = view.mode_container.content.controls[0].content.controls[0]
    assert borrower_toolbar.controls[0].content is view.borrower_search
    borrower_actions = borrower_toolbar.controls[1].content.controls
    assert borrower_actions[0].content == "เพิ่มผู้ยืม"
    assert borrower_actions[1].content == "รีเฟรช"
