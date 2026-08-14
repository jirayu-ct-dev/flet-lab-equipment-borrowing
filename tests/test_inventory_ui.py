import flet as ft

from app.views.inventory import InventoryView


def test_inventory_view_initializes_with_service_and_state() -> None:
    view = InventoryView()

    assert isinstance(view, ft.Container)
    assert view.content is not None
    assert not hasattr(view, "management_content")


def test_inventory_view_renders_units_as_table() -> None:
    view = InventoryView()

    surface = view.unit_table_container.content
    table = surface.content.controls[0]
    assert isinstance(table, ft.DataTable)
    assert len(table.columns) == 5
    assert table.columns[0].label.value == "รหัสอุปกรณ์"

    surface.on_size_change(type("Size", (), {"width": 1200})())
    assert table.width == 1176
    surface.on_size_change(type("Size", (), {"width": 430})())
    assert table.width == 1000


def test_inventory_filter_toolbar_keeps_search_filter_and_reset_together() -> None:
    view = InventoryView()

    filter_card = view.content.controls[1]
    toolbar = filter_card.content.controls[0]
    assert isinstance(toolbar, ft.ResponsiveRow)
    assert toolbar.controls[0].content is view.search_field
    actions = toolbar.controls[1].content.controls
    assert actions == [view.status_dropdown, view.reset_button]
    assert len(filter_card.content.controls) == 1
    assert not hasattr(view, "count_badge")
    assert view.reset_button.content == "รีเซ็ต"
    assert view.search_field.border_radius == view.status_dropdown.border_radius == 12
    assert view.reset_button.style.shape.radius == 12
