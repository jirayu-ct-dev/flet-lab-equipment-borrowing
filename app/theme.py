import flet as ft

APP_TITLE = "Lab Equipment Borrowing"
PAGE_PADDING = 32
NAV_WIDTH = 279
CONTROL_RADIUS = 12

# Color Tokens
COLOR_PRIMARY = ft.Colors.BLUE_600
COLOR_PRIMARY_DARK = ft.Colors.BLUE_800
COLOR_BG = ft.Colors.SURFACE_CONTAINER_LOW
COLOR_SURFACE = ft.Colors.SURFACE
COLOR_SIDEBAR_BG = ft.Colors.SURFACE
COLOR_SIDEBAR_TEXT = ft.Colors.ON_SURFACE_VARIANT
COLOR_SIDEBAR_ACTIVE = ft.Colors.PRIMARY

COLOR_TEXT_PRIMARY = ft.Colors.ON_SURFACE
COLOR_TEXT_SECONDARY = ft.Colors.ON_SURFACE_VARIANT
COLOR_BORDER = ft.Colors.OUTLINE_VARIANT

# Status Badges Theme (Foreground, Background, Icon)
STATUS_THEMES = {
    "available": {
        "text": "พร้อมใช้งาน",
        "color": ft.Colors.GREEN_700,
        "bgcolor": ft.Colors.GREEN_50,
        "icon": ft.Icons.CHECK_CIRCLE_OUTLINED,
    },
    "borrowed": {
        "text": "ถูกยืม",
        "color": ft.Colors.BLUE_700,
        "bgcolor": ft.Colors.BLUE_50,
        "icon": ft.Icons.SCHEDULE,
    },
    "maintenance": {
        "text": "กำลังบำรุงรักษา",
        "color": ft.Colors.AMBER_800,
        "bgcolor": ft.Colors.AMBER_50,
        "icon": ft.Icons.BUILD_OUTLINED,
    },
    "reported_lost": {
        "text": "แจ้งหาย",
        "color": ft.Colors.RED_700,
        "bgcolor": ft.Colors.RED_50,
        "icon": ft.Icons.WARNING_AMBER_ROUNDED,
    },
    "retired": {
        "text": "ปลดระวาง",
        "color": ft.Colors.GREY_700,
        "bgcolor": ft.Colors.GREY_100,
        "icon": ft.Icons.DELETE_OUTLINED,
    },
    "active": {
        "text": "ใช้งาน",
        "color": ft.Colors.GREEN_700,
        "bgcolor": ft.Colors.GREEN_50,
        "icon": ft.Icons.CHECK_CIRCLE_OUTLINED,
    },
    "inactive": {
        "text": "ไม่ใช้งาน",
        "color": ft.Colors.GREY_700,
        "bgcolor": ft.Colors.GREY_100,
        "icon": ft.Icons.CANCEL_OUTLINED,
    },
    "overdue": {
        "text": "เกินกำหนด",
        "color": ft.Colors.RED_700,
        "bgcolor": ft.Colors.RED_50,
        "icon": ft.Icons.ERROR_OUTLINED,
    },
    "partial": {
        "text": "คืนบางส่วน",
        "color": ft.Colors.ORANGE_800,
        "bgcolor": ft.Colors.ORANGE_50,
        "icon": ft.Icons.DONUT_LARGE,
    },
    "closed": {
        "text": "ปิดสัญญา",
        "color": ft.Colors.GREY_700,
        "bgcolor": ft.Colors.GREY_100,
        "icon": ft.Icons.TASK_ALT,
    },
    "open": {
        "text": "รอดำเนินการ",
        "color": ft.Colors.RED_700,
        "bgcolor": ft.Colors.RED_50,
        "icon": ft.Icons.REPORT_PROBLEM_OUTLINED,
    },
    "resolved": {
        "text": "ปิดเคสแล้ว",
        "color": ft.Colors.GREEN_700,
        "bgcolor": ft.Colors.GREEN_50,
        "icon": ft.Icons.TASK_ALT,
    },
}

NAVIGATION_ITEMS = [
    {"label": "Dashboard", "icon": ft.Icons.DASHBOARD_OUTLINED, "selected_icon": ft.Icons.DASHBOARD, "route": "dashboard"},
    {"label": "อุปกรณ์", "icon": ft.Icons.INVENTORY_2_OUTLINED, "selected_icon": ft.Icons.INVENTORY_2, "route": "inventory"},
    {"label": "คนในระบบ", "icon": ft.Icons.PEOPLE_OUTLINED, "selected_icon": ft.Icons.PEOPLE, "route": "people"},
    {"label": "ทำรายการยืม", "icon": ft.Icons.ASSIGNMENT_OUTLINED, "selected_icon": ft.Icons.ASSIGNMENT, "route": "borrow"},
    {"label": "คืนอุปกรณ์", "icon": ft.Icons.RECEIPT_LONG_OUTLINED, "selected_icon": ft.Icons.RECEIPT_LONG, "route": "returns"},
    {"label": "ประวัติ", "icon": ft.Icons.HISTORY_OUTLINED, "selected_icon": ft.Icons.HISTORY, "route": "history"},
]
