from app.services.fake_services import FakeInventoryService


def test_search_units_supports_status_filter() -> None:
    service = FakeInventoryService()

    available = service.search_units(keyword="", status="available")
    borrowed = service.search_units(keyword="", status="borrowed")

    assert available
    assert borrowed
    assert all(unit.status == "available" for unit in available)
    assert all(unit.status == "borrowed" for unit in borrowed)


def test_duplicate_asset_code_is_rejected() -> None:
    service = FakeInventoryService()

    first = service.create_unit(asset_code="AST-007", equipment_id="eq-1", location="Lab C")
    second = service.create_unit(asset_code="AST-007", equipment_id="eq-1", location="Lab D")

    assert first.asset_code == "AST-007"
    assert second is None


def test_update_unit_status_records_location_and_reason() -> None:
    service = FakeInventoryService()
    unit = service.create_unit(asset_code="AST-008", equipment_id="eq-1", location="Lab C")

    updated = service.update_unit_status(unit.id, "maintenance", location="Repair Room", reason="Inspection")

    assert updated is not None
    assert updated.status == "maintenance"
    assert updated.location == "Repair Room"
    assert updated.note == "Inspection"
