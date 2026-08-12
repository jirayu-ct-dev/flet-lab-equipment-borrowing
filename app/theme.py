import flet as ft

APP_TITLE = "Lab Equipment Borrowing"
PAGE_PADDING = 24
NAV_WIDTH = 240

# Color Tokens
COLOR_PRIMARY = ft.Colors.BLUE_600
COLOR_PRIMARY_DARK = ft.Colors.BLUE_800
COLOR_BG = "#F8FAFC"
COLOR_SURFACE = ft.Colors.WHITE
COLOR_SIDEBAR_BG = "#0F172A"
COLOR_SIDEBAR_TEXT = "#94A3B8"
COLOR_SIDEBAR_ACTIVE = "#38BDF8"

COLOR_TEXT_PRIMARY = "#0F172A"
COLOR_TEXT_SECONDARY = "#64748B"
COLOR_BORDER = "#E2E8F0"

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
}

NAVIGATION_ITEMS = [
    {"label": "คลังอุปกรณ์", "icon": ft.Icons.INVENTORY_2_OUTLINED, "selected_icon": ft.Icons.INVENTORY_2, "route": "inventory"},
    {"label": "เจ้าหน้าที่ & ผู้ยืม", "icon": ft.Icons.PEOPLE_OUTLINED, "selected_icon": ft.Icons.PEOPLE, "route": "staff_borrowers"},
    {"label": "ยืมอุปกรณ์", "icon": ft.Icons.ASSIGNMENT_OUTLINED, "selected_icon": ft.Icons.ASSIGNMENT, "route": "borrow_flow"},
    {"label": "สัญญายืม & คืน", "icon": ft.Icons.RECEIPT_LONG_OUTLINED, "selected_icon": ft.Icons.RECEIPT_LONG, "route": "loans"},
    {"label": "ประวัติการใช้งาน", "icon": ft.Icons.HISTORY_OUTLINED, "selected_icon": ft.Icons.HISTORY, "route": "history"},
]
