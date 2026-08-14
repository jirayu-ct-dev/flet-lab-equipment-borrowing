import flet as ft

from app.services.fake_services import FakeInventoryService
from app.views.dashboard import DashboardView


def test_dashboard_has_three_management_dialogs() -> None:
    view = DashboardView(FakeInventoryService())

    view._open_category_dialog(None)
    assert view.category_dialog.open is True

    view.category_dialog.open = False
    view._open_equipment_dialog(None)
    assert view.equipment_dialog.open is True

    view.equipment_dialog.open = False
    view._open_manage_dialog(None)
    assert view.manage_dialog.open is True


def test_dashboard_updates_inventory_from_management_dialog() -> None:
    service = FakeInventoryService()
    view = DashboardView(service)
    view.manage_unit.value = "unit-1"
    view.manage_action.value = "relocate"
    view.manage_location.value = "Lab B"
    view.manage_reason.value = "ย้ายชั้นเก็บ"

    view._save_management(None)

    assert service.get_unit_by_id("unit-1").location == "Lab B"
    assert view.feedback.value == "อัปเดตคลังเรียบร้อย"


def test_dashboard_is_a_flet_container() -> None:
    assert isinstance(DashboardView(), ft.Container)


def test_dashboard_shows_inventory_table() -> None:
    view = DashboardView(FakeInventoryService())

    assert isinstance(view.table_container.content, ft.Row)
    table = view.table_container.content.controls[0]
    assert isinstance(table, ft.DataTable)
    assert len(table.columns) == 5
    assert [column.expand for column in table.columns] == [2, 3, 2, 2, 3]


def test_dashboard_shows_inventory_cards_on_mobile() -> None:
    view = DashboardView(FakeInventoryService(), mobile=True)

    content = view.table_container.content
    assert isinstance(content, ft.Column)
    assert len(content.controls) == 5
    assert all(isinstance(card, ft.Container) for card in content.controls)


def test_dashboard_switches_table_and_cards_across_breakpoint() -> None:
    view = DashboardView(FakeInventoryService())

    assert isinstance(view.table_container.content, ft.Row)

    view._handle_resize(type("Size", (), {"width": 430})())
    assert isinstance(view.table_container.content, ft.Column)

    view._handle_resize(type("Size", (), {"width": 1440})())
    assert isinstance(view.table_container.content, ft.Row)


def test_dashboard_header_contains_three_wrapping_actions() -> None:
    view = DashboardView(FakeInventoryService())
    header = view.content.controls[0]
    actions = header.content.controls[1].content

    assert len(actions.controls) == 3
    assert actions.wrap is True


def test_dashboard_mobile_actions_sit_in_one_row_with_short_labels() -> None:
    view = DashboardView(FakeInventoryService(), mobile=True)
    header = view.content.controls[0]
    actions = header.content.controls[1].content

    assert isinstance(actions, ft.Row)
    assert len(actions.controls) == 3
    assert actions.wrap is False
    assert [action.content for action in actions.controls] == [
        "เพิ่มหมวด",
        "เพิ่มอุปกรณ์",
        "จัดการ",
    ]
    assert all(action.expand is True for action in actions.controls)


def test_dashboard_mobile_summary_uses_two_columns() -> None:
    view = DashboardView(FakeInventoryService(), mobile=True)
    summary = view.content.controls[1]

    assert isinstance(summary, ft.ResponsiveRow)
    assert len(summary.controls) == 4
    assert all(card.col["xs"] == 6 for card in summary.controls)


def test_dashboard_table_fills_desktop_and_keeps_mobile_minimum_width() -> None:
    view = DashboardView(FakeInventoryService())

    view._handle_table_size(type("Size", (), {"width": 1200})())
    assert view.inventory_table.width == 1200

    view._handle_table_size(type("Size", (), {"width": 430})())
    assert view.inventory_table.width == 900


def test_dashboard_modal_fields_stretch_to_dialog_width() -> None:
    view = DashboardView(FakeInventoryService())

    assert view.equipment_dialog.content.width == 600
    assert (
        view.equipment_dialog.content.content.horizontal_alignment
        == ft.CrossAxisAlignment.STRETCH
    )


def test_dashboard_uses_clear_inventory_levels() -> None:
    view = DashboardView(FakeInventoryService())

    assert view.category_name.label == "ชื่อหมวดหมู่"
    assert view.equipment_category.label == "หมวดหมู่"
    assert view.equipment_name.label == "ชื่ออุปกรณ์"
    assert view.equipment_asset_code.label == "รหัสอุปกรณ์"
    assert isinstance(view.equipment_category, ft.Dropdown)
    assert view.equipment_category.expand is True
    assert view.equipment_category_row.controls == [view.equipment_category]
    equipment_fields = view.equipment_dialog.content.content.controls
    assert equipment_fields[1] is view.equipment_asset_code
    assert equipment_fields[2] is view.equipment_name
    assert equipment_fields[3] is view.equipment_category_row
    assert view.equipment_category.expanded_insets is None
    assert view.equipment_category.menu_width == 600

    view._handle_category_dropdown_size(type("Size", (), {"width": 420})())
    assert view.equipment_category.menu_width == 420
    assert view.manage_unit.expand is True
    assert view.manage_action.expand is True
    assert view.manage_unit_row.controls == [view.manage_unit]
    assert view.manage_action_row.controls == [view.manage_action]
    assert view.manage_location.label == "สถานที่เก็บใหม่"

    header = view.content.controls[0]
    actions = header.content.controls[1].content
    assert [action.content for action in actions.controls[:2]] == [
        "เพิ่มหมวดหมู่",
        "เพิ่มอุปกรณ์",
    ]

    table = view.table_container.content.controls[0]
    assert table.columns[2].label.value == "หมวดหมู่"


def test_dashboard_creates_category_and_uses_it_in_equipment_dropdown() -> None:
    view = DashboardView(FakeInventoryService())
    view.category_name.value = "หนังสือวิทยาศาสตร์"

    view._save_category(None)

    assert view.feedback.value == "เพิ่มหมวดหมู่เรียบร้อย"
    assert any(
        option.text == "หนังสือวิทยาศาสตร์"
        for option in view.equipment_category.options
    )
