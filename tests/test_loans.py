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

    view._select_loan(None, loan)
    assert view.selected_loan is not None
    assert view.selected_loan.id == "loan-1"
    assert view.selected_unit_ids == ["unit-2"]

    view._handle_confirm_return(None)
    assert view.feedback.value.startswith("Returned 1 unit(s) for loan loan-1")
    assert view.selected_loan is None
