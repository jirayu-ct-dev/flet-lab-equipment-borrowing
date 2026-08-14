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


def test_loans_view_renders_loans_as_cards_on_mobile() -> None:
    view = LoansView(FakeInventoryService(), mobile=True)

    content = view.loan_container.content
    assert isinstance(content, ft.Column)
    assert len(content.controls) == 1
    assert isinstance(content.controls[0], ft.Container)


def test_loans_mobile_card_keeps_action_out_of_header_and_readable() -> None:
    view = LoansView(FakeInventoryService(), mobile=True)
    loan = view.service.get_loan("loan-1")

    rows = view.loan_container.content.controls[0].content.controls

    header = rows[0]
    assert isinstance(header, ft.Row)
    assert isinstance(header.controls[0], ft.Icon)
    assert isinstance(header.controls[1], ft.Text)
    assert header.controls[1].value == f"รายการยืม {loan.id}"
    assert isinstance(header.controls[-1], ft.Container)

    first_grid = rows[1]
    assert isinstance(first_grid, ft.Row)
    first_cell = first_grid.controls[0].content.controls
    assert first_cell[0].value == "ครบกำหนด"
    assert first_cell[1].value == loan.due_date
    second_cell = first_grid.controls[1].content.controls
    assert second_cell[0].value == "คืนแล้ว"

    footer = rows[-1]
    assert isinstance(footer, ft.Row)
    button = footer.controls[0]
    assert isinstance(button, ft.Button)
    assert button.content == "บันทึกการคืน"
    assert button.expand is True


def test_loans_view_switches_table_and_cards_across_breakpoint() -> None:
    view = LoansView(FakeInventoryService())

    assert isinstance(view.loan_container.content.content.controls[0], ft.DataTable)

    view._handle_resize(type("Size", (), {"width": 430})())
    assert isinstance(view.loan_container.content, ft.Column)

    view._handle_resize(type("Size", (), {"width": 1440})())
    assert isinstance(view.loan_container.content.content.controls[0], ft.DataTable)


def test_loans_view_uses_full_width_filter_and_stacked_return_fields() -> None:
    view = LoansView(FakeInventoryService())

    filter_column = view.content.controls[1].content
    assert filter_column.controls[0] is view.search_field
    filter_row = filter_column.controls[1]
    assert isinstance(filter_row, ft.Row)
    assert filter_row.controls[0] is view.filter_dropdown
    refresh_button = filter_row.controls[1]
    assert refresh_button.content == "รีเฟรช"
    assert refresh_button.height == 52
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


def test_loans_refresh_keeps_table_responsive_width() -> None:
    view = LoansView(FakeInventoryService())
    view._handle_resize(type("Size", (), {"width": 1600})())

    view._handle_refresh(None)

    table = view.loan_container.content.content.controls[0]
    assert table.width == 1576


def test_loans_view_searches_by_loan_or_borrower_code() -> None:
    view = LoansView(FakeInventoryService())

    view.search_field.value = "BR-001"
    view._handle_search(None)
    table = view.loan_container.content.content.controls[0]
    assert len(table.rows) == 1

    view.search_field.value = "ไม่พบรายการ"
    view._handle_search(None)
    assert "ไม่พบรายการยืม" in view.loan_container.content.content.controls[1].value
