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
