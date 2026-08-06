import flet as ft

APP_TITLE = "Lab Equipment Borrowing"
PAGE_PADDING = 24
NAV_WIDTH = 220

NAVIGATION_ITEMS = [
    {"label": "Inventory", "icon": ft.Icons.INVENTORY_2_OUTLINED, "route": "inventory"},
    {"label": "Staff", "icon": ft.Icons.PEOPLE_OUTLINED, "route": "staff"},
    {"label": "Borrowers", "icon": ft.Icons.PERSON_OUTLINED, "route": "borrowers"},
    {"label": "Loans", "icon": ft.Icons.PAYMENT_OUTLINED, "route": "loans"},
    {"label": "History", "icon": ft.Icons.HISTORY_OUTLINED, "route": "history"},
]
