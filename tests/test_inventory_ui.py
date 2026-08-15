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
    assert table.width == 1174
    surface.on_size_change(type("Size", (), {"width": 430})())
    assert table.width == 1000


def test_inventory_view_renders_units_as_cards_on_mobile() -> None:
    view = InventoryView(mobile=True)

    content = view.unit_table_container.content
    assert isinstance(content, ft.Column)
    assert len(content.controls) == 5
    assert all(isinstance(card, ft.Container) for card in content.controls)


def test_inventory_view_switches_table_and_cards_across_breakpoint() -> None:
    view = InventoryView()

    assert isinstance(view.unit_table_container.content.content.controls[0], ft.DataTable)

    view._handle_resize(type("Size", (), {"width": 430})())
    assert isinstance(view.unit_table_container.content, ft.Column)

    view._handle_resize(type("Size", (), {"width": 1440})())
    assert isinstance(view.unit_table_container.content.content.controls[0], ft.DataTable)


def test_inventory_mobile_filter_uses_two_stacked_rows() -> None:
    view = InventoryView(mobile=True)

    filter_column = view.content.controls[1].content
    top_row = filter_column.controls[0]
    bottom_row = filter_column.controls[1]
    assert isinstance(top_row, ft.Row)
    assert isinstance(bottom_row, ft.Row)
    assert top_row.controls == [view.search_field, view.reset_button]
    assert bottom_row.controls == [view.status_dropdown, view.category_dropdown]
    assert view.reset_button.icon is None
    assert view.status_dropdown.width is None
    assert view.status_dropdown.expand is True


def test_inventory_filter_responsive_props_switch_across_breakpoint() -> None:
    view = InventoryView()

    view._handle_resize(type("Size", (), {"width": 430})())
    filter_column = view.content.controls[1].content
    assert isinstance(filter_column, ft.Column)
    assert filter_column.controls[0].controls == [view.search_field, view.reset_button]
    assert filter_column.controls[1].controls == [view.status_dropdown, view.category_dropdown]
    assert view.status_dropdown.width is None
    assert view.status_dropdown.expand is True

    view._handle_resize(type("Size", (), {"width": 1440})())
    toolbar = view.content.controls[1].content.controls[0]
    assert isinstance(toolbar, ft.ResponsiveRow)
    actions = toolbar.controls[1].content.controls
    assert actions == [view.status_dropdown, view.category_dropdown, view.reset_button]
    assert view.status_dropdown.width == 180
    assert view.status_dropdown.expand is None


def test_inventory_reset_keeps_table_responsive_width() -> None:
    view = InventoryView()
    view._handle_resize(type("Size", (), {"width": 1200})())

    view._handle_reset(None)

    table = view.unit_table_container.content.content.controls[0]
    assert table.width == 1174


def test_inventory_reset_prefers_surface_reported_width() -> None:
    view = InventoryView()
    surface = view.unit_table_container.content
    surface.on_size_change(type("Size", (), {"width": 1200})())

    view._handle_reset(None)

    table = view.unit_table_container.content.content.controls[0]
    assert table.width == 1174
    assert view._surface_width == 1200


def test_inventory_filter_toolbar_keeps_search_filter_and_reset_together() -> None:
    view = InventoryView()

    filter_card = view.content.controls[1]
    toolbar = filter_card.content.controls[0]
    assert isinstance(toolbar, ft.ResponsiveRow)
    assert toolbar.controls[0].content is view.search_field
    actions = toolbar.controls[1].content.controls
    assert actions == [view.status_dropdown, view.category_dropdown, view.reset_button]
    assert not hasattr(view, "count_badge")
    assert view.reset_button.content == "รีเฟรช"
    assert view.reset_button.height == 52
    assert view.search_field.height == 52
    assert view.status_dropdown.height == 52
    assert view.search_field.border_radius == view.status_dropdown.border_radius == 12
    assert view.category_dropdown.border_radius == 12
    assert view.reset_button.style.shape.radius == 12
