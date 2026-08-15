import flet as ft

from app.services.fake_services import FakeInventoryService
from app.views.history import HistoryView


def test_fake_inventory_service_records_history_events() -> None:
    service = FakeInventoryService()
    events = service.list_history()

    assert events
    assert any(event.event_type == "borrowed" for event in events)
    assert any(event.asset_code == "AST-002" for event in events)


def test_history_view_search_filters_history() -> None:
    service = FakeInventoryService()
    view = HistoryView(service)

    view.borrower_search.value = "BR-001"
    view._handle_search(None)
    assert "filtered" in view.feedback.value.lower()

    view.borrower_search.value = ""
    view.asset_search.value = "AST-002"
    view._handle_search(None)
    assert "filtered" in view.feedback.value.lower()


def test_history_view_renders_events_as_table() -> None:
    view = HistoryView(FakeInventoryService())

    table = view.history_container.content.content.controls[0]
    assert isinstance(table, ft.DataTable)
    assert len(table.columns) == 7
    assert table.columns[0].label.value == "วันที่"


def test_history_view_renders_events_as_cards_on_mobile() -> None:
    view = HistoryView(FakeInventoryService(), mobile=True)

    content = view.history_container.content
    assert isinstance(content, ft.Column)
    assert len(content.controls) == 2
    assert all(isinstance(card, ft.Container) for card in content.controls)


def test_history_clear_keeps_table_responsive_width() -> None:
    view = HistoryView(FakeInventoryService())
    view._handle_resize(type("Size", (), {"width": 1600})())

    view._handle_clear(None)

    table = view.history_container.content.content.controls[0]
    assert table.width == 1576


def test_history_filter_uses_original_multi_row_layout() -> None:
    view = HistoryView(FakeInventoryService())

    filter_content = view.content.controls[1].content
    primary_row = filter_content.controls[1]
    secondary_row = filter_content.controls[2]
    button_row = filter_content.controls[3]

    assert isinstance(primary_row, ft.ResponsiveRow)
    assert primary_row.controls[0].content is view.borrower_search
    assert primary_row.controls[1].content is view.equipment_search
    assert [container.content for container in secondary_row.controls] == [
        view.asset_search,
        view.start_date,
        view.end_date,
    ]
    assert button_row.controls == [view.search_button, view.clear_button]
    assert view.search_button.content == "ค้นหาประวัติ"
    assert view.clear_button.content == "รีเฟรช"
