from app.services.fake_services import FakeInventoryService


def test_borrow_flow_can_create_draft_and_confirm() -> None:
    service = FakeInventoryService()
    service.create_staff("ST-100", "Test Staff")
    service.create_borrower("BR-100", "Test Borrower")

    draft = service.create_borrow_draft(
        borrower_code="BR-100",
        staff_code="ST-100",
        unit_ids=["unit-1"],
        borrow_date="2026-08-06",
        due_date="2026-08-10",
        purpose="Testing",
    )

    assert draft is not None
    assert draft.borrower_code == "BR-100"
    assert draft.staff_code == "ST-100"
    assert draft.unit_ids == ["unit-1"]

    confirmed = service.confirm_borrow_draft(draft.id)
    assert confirmed is not None
    assert confirmed.status == "active"


def test_borrow_flow_rejects_unavailable_units_and_updates_statuses() -> None:
    service = FakeInventoryService()
    service.create_staff("ST-100", "Test Staff")
    service.create_borrower("BR-100", "Test Borrower")
    service.update_unit_status("unit-2", "borrowed")

    draft = service.create_borrow_draft(
        borrower_code="BR-100",
        staff_code="ST-100",
        unit_ids=["unit-1", "unit-2"],
        borrow_date="2026-08-06",
        due_date="2026-08-10",
        purpose="Testing",
    )

    assert draft is None

    draft = service.create_borrow_draft(
        borrower_code="BR-100",
        staff_code="ST-100",
        unit_ids=["unit-1"],
        borrow_date="2026-08-06",
        due_date="2026-08-10",
        purpose="Testing",
    )

    confirmed = service.confirm_borrow_draft(draft.id)
    assert confirmed is not None
    assert service.get_unit_by_id("unit-1").status == "borrowed"
