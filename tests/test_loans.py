import flet as ft

from app.services.fake_services import FakeInventoryService, HistoryEvent
from app.views.loans import LoansView


def test_fake_inventory_service_can_return_active_loan_unit() -> None:
    service = FakeInventoryService()
    loan = service.get_loan("loan-1")

    assert loan is not None
    assert loan.status == "active"
    assert loan.returned_unit_ids == []

    result = service.return_loan_units(
        loan_id="loan-1",
        unit_ids=["unit-2"],
        outcome="returned",
        condition="Good condition",
    )

    assert result is not None
    assert result.status == "closed"
    assert result.returned_unit_ids == ["unit-2"]
    assert service.get_unit_by_id("unit-2").status == "available"


def test_loans_view_can_select_and_confirm_return() -> None:
    service = FakeInventoryService()
    view = LoansView(service)

    assert view.receiving_staff_dropdown.value == "ST-001"
    assert view.return_location_dropdown.value is not None

    loan = service.get_loan("loan-1")
    assert loan is not None

    view._open_return_dialog(None, loan)
    assert view.return_dialog.open is True
    assert view.selected_loan is not None
    assert view.selected_loan.id == "loan-1"
    assert view.selected_unit_ids == ["unit-2"]

    view._handle_confirm_return(None)
    assert view.feedback.value == "บันทึกการคืน 1 ชิ้นเรียบร้อย"
    assert view.selected_loan is None
    assert view.return_dialog.open is False


def test_loans_view_renders_returnable_loans_as_table() -> None:
    view = LoansView(FakeInventoryService())

    table = view.loan_container.content.content.controls[0]
    assert isinstance(table, ft.DataTable)
    assert len(table.columns) == 7
    assert table.columns[-1].label.value == "จัดการ"
    assert table.rows[0].cells[-1].content.content == "บันทึกการคืน"


def test_loans_view_uses_full_width_filter_and_stacked_return_fields() -> None:
    view = LoansView(FakeInventoryService())

    filter_layout = view.content.controls[1].content.controls[0]
    assert isinstance(filter_layout, ft.ResponsiveRow)
    assert filter_layout.controls[0].content is view.search_field
    filter_actions = filter_layout.controls[1].content.controls
    assert filter_actions[0] is view.filter_dropdown_row
    refresh_button = filter_actions[1]
    assert refresh_button.content == "รีเฟรชข้อมูล"
    assert view.filter_dropdown_row.width == 320
    assert view.filter_dropdown.expand is True
    assert view.filter_dropdown.border_radius == 12
    assert refresh_button.style.shape.radius == 12
    assert view.search_field.border_radius == 12

    dialog_controls = view.return_dialog.content.content.controls
    assert dialog_controls[2:6] == [
        view.return_action_row,
        view.return_notes,
        view.receiving_staff_row,
        view.return_location_row,
    ]
    assert view.return_dialog.content.content.horizontal_alignment == ft.CrossAxisAlignment.STRETCH
    assert all(row.width == float("inf") for row in dialog_controls[2:6] if isinstance(row, ft.Row))
    assert all(
        dropdown.expand is True
        for dropdown in (
            view.return_action_dropdown,
            view.receiving_staff_dropdown,
            view.return_location_dropdown,
        )
    )


def test_loans_view_searches_by_loan_or_borrower_code() -> None:
    view = LoansView(FakeInventoryService())

    view.search_field.value = "BR-001"
    view._handle_search(None)
    table = view.loan_container.content.content.controls[0]
    assert len(table.rows) == 1

    view.search_field.value = "ไม่พบรายการ"
    view._handle_search(None)
    assert "ไม่พบรายการยืม" in view.loan_container.content.content.controls[1].value
