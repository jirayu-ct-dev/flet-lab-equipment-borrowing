from app.services.fake_services import FakeInventoryService
from app.views.inventory import InventoryView


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


def test_relocate_unit_preserves_status_and_records_location() -> None:
    service = FakeInventoryService()
    unit = service.create_unit(asset_code="AST-008", equipment_id="eq-1", location="Lab C")

    updated = service.update_unit_status(unit.id, "relocate", location="Repair Room", reason="Move shelf")

    assert updated is not None
    assert updated.status == "available"
    assert updated.location == "Repair Room"
    assert updated.note == "Move shelf"


def test_complete_repair_requires_maintenance_unit() -> None:
    service = FakeInventoryService()

    repaired = service.update_unit_status("unit-3", "maintenance", location="Lab A", reason="Repair complete")
    invalid = service.update_unit_status("unit-1", "maintenance", location="Lab A", reason="Not under repair")

    assert repaired is not None
    assert repaired.status == "available"
    assert invalid is None


def test_inventory_view_creates_unit_for_selected_equipment() -> None:
    service = FakeInventoryService()
    view = InventoryView(service)
    view.equipment_dropdown.value = "eq-2"
    view.asset_code_field.value = "AST-009"
    view.location_field.value = "Lab D"

    view._handle_create_unit(None)

    created = service.get_unit("AST-009")
    assert created is not None
    assert created.equipment_name == "Microscope"
