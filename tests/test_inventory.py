import flet as ft

from app.services.fake_services import FakeInventoryService
from app.views.inventory import build_inventory_view


def test_search_units_filters_by_keyword() -> None:
    service = FakeInventoryService()

    results = service.search_units("microscope")

    assert results
    assert all("microscope" in unit.equipment_name.lower() for unit in results)


def test_create_equipment_and_unit_updates_service_state() -> None:
    service = FakeInventoryService()

    equipment = service.create_equipment("Tablet", "EQ-300", "IT")
    unit = service.create_unit(asset_code="AST-006", equipment_id=equipment.id, location="Lab B")

    assert equipment.equipment_code == "EQ-300"
    assert unit.asset_code == "AST-006"
    assert service.get_unit("AST-006") is not None


def test_build_inventory_view_returns_container() -> None:
    view = build_inventory_view(FakeInventoryService())

    assert isinstance(view, ft.Container)
