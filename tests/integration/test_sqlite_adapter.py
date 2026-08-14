from app.database import connection
from app.services.sqlite_adapter import SQLiteInventoryAdapter


def test_adapter_persists_inventory_and_loan_flow(tmp_path) -> None:
    database_path = tmp_path / "adapter.db"
    service = SQLiteInventoryAdapter(database_path)

    equipment = service.create_equipment("Laptop", "EQ-001", "IT")
    staff = service.create_staff("ST-001", "Operator")
    borrower = service.create_borrower("BR-001", "Student")

    assert equipment is not None
    assert staff is not None
    assert borrower is not None

    unit = service.create_unit(
        asset_code="AST-001",
        equipment_id=equipment.id,
        location="Lab A",
    )
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
    assert service.get_unit_by_id(unit.id).status == "borrowed"

    location = service.list_locations()[0]
    returned = service.return_loan_units(
        draft.id,
        [unit.id],
        "returned",
        staff_code=staff.staff_code,
        location_id=location.id,
    )
    assert returned is not None
    assert returned.status == "closed"

    history = service.list_history(asset_code="AST-001")
    assert {event.event_type for event in history} >= {"acquire", "borrowed", "available"}
    assert all(event.asset_code == "AST-001" for event in history)
    assert service.list_history(borrower_query="BR-001")
    assert service.list_history(equipment_query="Laptop")
    assert service.list_history(asset_code="DOES-NOT-EXIST") == []

    restarted = SQLiteInventoryAdapter(database_path)
    assert restarted.get_unit_by_asset_code("AST-001").status == "available"
    assert restarted.list_loans()[0].status == "closed"


def test_adapter_persists_categories_and_creates_equipment_from_category(tmp_path) -> None:
    database_path = tmp_path / "categories.db"
    service = SQLiteInventoryAdapter(database_path)

    category = service.create_category("IT")
    assert category is not None
    assert service.create_category("it") is None

    unit = service.create_inventory_item(
        name="จอคอม",
        category_id=category.id,
        asset_code="MON-001",
        location="Lab A",
    )

    assert unit is not None
    assert unit.equipment_name == "จอคอม"
    assert unit.category == "IT"
    with connection(database_path) as database:
        stored_category_id = database.execute(
            "SELECT category_id FROM equipment WHERE equipment_code = 'MON-001'"
        ).fetchone()["category_id"]
    assert stored_category_id == int(category.id)
    restarted = SQLiteInventoryAdapter(database_path)
    assert restarted.list_categories() == [category]
    assert restarted.get_unit_by_asset_code("MON-001") is not None


def test_adapter_uses_inventory_adjustment_services(tmp_path) -> None:
    service = SQLiteInventoryAdapter(tmp_path / "adjustments.db")
    equipment = service.create_equipment("Camera", "EQ-002", "Media")
    assert equipment is not None
    unit = service.create_unit(asset_code="CAM-001", equipment_id=equipment.id, location="Studio")
    assert unit is not None

    relocated = service.update_unit_status(unit.id, "relocate", location="Storage", reason="Move cabinet")
    assert relocated is not None
    assert relocated.status == "available"
    assert relocated.location == "Storage"

    retired = service.update_unit_status(unit.id, "retired", reason="End of life")
    assert retired is not None
    assert retired.status == "retired"
    assert service.update_unit_status(unit.id, "relocate", location="Lab", reason="Invalid") is None

    history = service.list_history(asset_code="CAM-001")
    assert {event.event_type for event in history} >= {"acquire", "relocate", "retire"}


def test_adapter_recovers_legacy_lost_case_from_inventory(tmp_path) -> None:
    service = SQLiteInventoryAdapter(tmp_path / "lost-case.db")
    equipment = service.create_equipment("Camera", "EQ-003", "Media")
    staff = service.create_staff("ST-003", "Approver")
    borrower = service.create_borrower("BR-003", "Student")
    assert equipment and staff and borrower
    unit = service.create_unit(asset_code="CAM-LOST", equipment_id=equipment.id, location="Studio")
    assert unit is not None
    draft = service.create_and_confirm_borrow(
        borrower_code=borrower.borrower_code,
        staff_code=staff.staff_code,
        unit_ids=[unit.id],
        borrow_date="2026-08-10",
        due_date="2026-08-13",
        purpose="Field work",
    )
    assert draft is not None
    assert service.return_loan_units(
        draft.id,
        [unit.id],
        "reported_lost",
        staff_code=staff.staff_code,
    ) is not None

    assert service.list_lost_cases(status="open")[0].asset_code == "CAM-LOST"
    recovered = service.update_unit_status(
        unit.id,
        "lost_recovered",
        location="Recovered shelf",
        reason="Found in storage",
    )

    assert recovered is not None
    assert recovered.status == "available"
    assert recovered.location == "Recovered shelf"
    assert service.list_lost_cases(status="open") == []
    assert "lost_resolved" in {
        event.event_type for event in service.list_history(asset_code="CAM-LOST")
    }
