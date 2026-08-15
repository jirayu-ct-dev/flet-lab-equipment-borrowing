from app.services.fake_services import FakeInventoryService
from app.services.sqlite_adapter import SQLiteInventoryAdapter


def test_fake_lists_loans_for_seeded_borrower() -> None:
    service = FakeInventoryService()

    loans = service.list_loans_for_borrower(1)

    assert [loan.id for loan in loans] == ["loan-1"]
    assert all(loan.borrower_code == "BR-001" for loan in loans)


def test_fake_returns_empty_for_unknown_borrower() -> None:
    service = FakeInventoryService()

    assert service.list_loans_for_borrower(999) == []
    assert service.list_loans_for_borrower(0) == []


def test_fake_applies_filter_type_to_borrower_loans() -> None:
    service = FakeInventoryService()
    loan = service.get_loan("loan-1")
    assert loan is not None

    assert service.list_loans_for_borrower(1, filter_type="soon") == [loan]
    assert service.list_loans_for_borrower(1, filter_type="today") == []
    assert service.list_loans_for_borrower(1, filter_type="overdue") == []


def test_sqlite_adapter_lists_loans_for_borrower(tmp_path) -> None:
    service = SQLiteInventoryAdapter(tmp_path / "my-loans.db")
    equipment = service.create_equipment("Laptop", "EQ-001", "IT")
    staff = service.create_staff("ST-001", "Operator")
    borrower = service.create_borrower("BR-001", "Student")
    other_borrower = service.create_borrower("BR-002", "Other")
    unit = service.create_unit(asset_code="AST-001", equipment_id=equipment.id, location="Lab A")
    assert unit is not None
    draft = service.create_and_confirm_borrow(
        borrower_code=borrower.borrower_code,
        staff_code=staff.staff_code,
        unit_ids=[unit.id],
        borrow_date="2026-08-12",
        due_date="2026-08-15",
        purpose="Lab work",
    )
    assert draft is not None

    loans = service.list_loans_for_borrower(int(borrower.id))

    assert [loan.id for loan in loans] == [draft.id]
    assert loans[0].borrower_code == "BR-001"
    assert service.list_loans_for_borrower(int(other_borrower.id)) == []

    restarted = SQLiteInventoryAdapter(tmp_path / "my-loans.db")
    assert [loan.id for loan in restarted.list_loans_for_borrower(int(borrower.id))] == [draft.id]
    assert restarted.list_loans() == service.list_loans()
