import flet as ft

from app.contracts import AppUser, RecordStatus, Role
from app.services.fake_services import FakeInventoryService
from app.views.my_loans import MyLoansView
from tests.test_auth_fixtures import borrower_user


class SpyLoanService(FakeInventoryService):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[int, str | None]] = []

    def list_loans_for_borrower(
        self, borrower_id: int, *, filter_type: str | None = None
    ):
        self.calls.append((borrower_id, filter_type))
        return super().list_loans_for_borrower(
            borrower_id, filter_type=filter_type
        )


def _user_without_borrower() -> AppUser:
    return AppUser(
        id=3,
        role=Role.USER,
        display_name="ผู้ใช้ที่ไม่มีข้อมูลผู้ยืม",
        email="ghost@lab.local",
        staff_id=None,
        borrower_id=None,
        status=RecordStatus.ACTIVE,
        must_change_password=False,
        last_login_at=None,
    )


def test_my_loans_view_renders_desktop_table_for_borrower() -> None:
    view = MyLoansView(FakeInventoryService(), current_user=borrower_user())

    surface = view.loan_container.content
    table = surface.content.controls[0]
    assert isinstance(table, ft.DataTable)
    assert [column.label.value for column in table.columns] == [
        "รายการ",
        "ครบกำหนด",
        "สถานะ",
        "คืนแล้ว",
        "ผู้บันทึก",
    ]
    assert len(table.rows) == 1
    assert table.rows[0].cells[0].content.value == "รายการยืม loan-1"
    assert table.rows[0].cells[3].content.value == "0 / 1 ชิ้น"
    assert table.rows[0].cells[4].content.value == "ST-001"


def test_my_loans_view_empty_state_without_borrower_link() -> None:
    view = MyLoansView(FakeInventoryService(), current_user=_user_without_borrower())

    state = view.loan_container.content
    assert "ไม่พบรายการยืม" in state.content.controls[1].value
    assert "คุณยังไม่มีรายการยืมในขณะนี้" in state.content.controls[2].value


def test_my_loans_view_empty_state_for_unknown_borrower_id() -> None:
    unknown_user = AppUser(
        id=4,
        role=Role.USER,
        display_name="ผู้ใช้ที่ไม่มีรายการยืม",
        email=None,
        staff_id=None,
        borrower_id=999,
        status=RecordStatus.ACTIVE,
        must_change_password=False,
        last_login_at=None,
    )
    view = MyLoansView(FakeInventoryService(), current_user=unknown_user)

    state = view.loan_container.content
    assert "ไม่พบรายการยืม" in state.content.controls[1].value


def test_my_loans_view_renders_cards_on_mobile() -> None:
    view = MyLoansView(
        FakeInventoryService(), current_user=borrower_user(), mobile=True
    )

    content = view.loan_container.content
    assert isinstance(content, ft.Column)
    assert isinstance(content.controls[0], ft.Container)
    header = content.controls[0].content.controls[0]
    assert isinstance(header, ft.Row)
    assert header.controls[1].value == "รายการยืม loan-1"


def test_my_loans_view_filters_by_search_query() -> None:
    view = MyLoansView(FakeInventoryService(), current_user=borrower_user())

    view.search_field.value = "loan-1"
    view._handle_search(None)
    table = view.loan_container.content.content.controls[0]
    assert len(table.rows) == 1

    view.search_field.value = "ไม่พบรายการนี้"
    view._handle_search(None)
    state = view.loan_container.content
    assert "ไม่พบรายการยืม" in state.content.controls[1].value


def test_my_loans_view_delegates_to_list_loans_for_borrower() -> None:
    spy = SpyLoanService()
    view = MyLoansView(spy, current_user=borrower_user())

    assert spy.calls == [(1, "all")]

    view.filter_dropdown.value = "overdue"
    view._handle_filter_change(None)

    assert spy.calls == [(1, "all"), (1, "overdue")]


def test_my_loans_view_switches_table_and_cards_across_breakpoint() -> None:
    view = MyLoansView(FakeInventoryService(), current_user=borrower_user())

    assert isinstance(view.loan_container.content.content.controls[0], ft.DataTable)

    view._handle_resize(type("Size", (), {"width": 430})())
    assert isinstance(view.loan_container.content, ft.Column)

    view._handle_resize(type("Size", (), {"width": 1440})())
    assert isinstance(view.loan_container.content.content.controls[0], ft.DataTable)


def test_my_loans_mobile_filter_stacks_search_above_dropdown() -> None:
    view = MyLoansView(
        FakeInventoryService(), current_user=borrower_user(), mobile=True
    )

    filter_column = view.content.controls[1].content
    assert isinstance(filter_column, ft.Column)
    assert filter_column.controls[0] is view.search_field
    row = filter_column.controls[1]
    assert isinstance(row, ft.Row)
    assert row.controls[0] is view.filter_dropdown
    assert view.filter_dropdown.width is None
    assert view.filter_dropdown.expand is True
