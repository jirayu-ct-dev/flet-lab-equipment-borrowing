import flet as ft

from app.views.inventory import InventoryView


def test_inventory_view_initializes_with_service_and_state() -> None:
    view = InventoryView()

    assert view.equipment_dropdown.value == "eq-1"

    assert isinstance(view, ft.Container)
    assert view.content is not None
