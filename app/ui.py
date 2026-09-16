from __future__ import annotations

import asyncio
from datetime import date, timedelta
from pathlib import Path

import flet as ft
from flet.controls.services.url_launcher import UrlLauncher

from app.database import bangkok_today
from app.errors import AppError
from app.import_users import ImportPreview, import_preview, preview_users, template_bytes
from app.line import LineMessenger, provider
from app.models import LineMessage, User
from app.service import AppService


PRIMARY = "#1a71f6"
CANVAS = "#f7f7f7"
SURFACE = "#ffffff"
SOFT = "#f1f5f9"
TEXT = "#323130"
MUTED = "#737373"
BORDER = "#d1d1d1"
SUCCESS = "#177245"
WARNING = "#a15c00"
DANGER = "#b42318"

ROLE_LABELS = {"admin": "ผู้ดูแลระบบ", "borrower": "ผู้ยืม"}
TYPE_LABELS = {"student": "นักศึกษา", "teacher": "อาจารย์", "staff": "เจ้าหน้าที่"}
STATUS_LABELS = {
    "active": "ใช้งาน",
    "inactive": "ปิดใช้งาน",
    "available": "พร้อมยืม",
    "borrowed": "ถูกยืม",
    "completed": "คืนครบแล้ว",
    "overdue": "เกินกำหนด",
}
STATUS_TONES = {
    "active": "#15803d",
    "available": "#15803d",
    "completed": "#0f766e",
    "borrowed": "#b45309",
    "overdue": "#b42318",
    "inactive": "#64748b",
}


def card(content: ft.Control, *, padding: int = 20) -> ft.Container:
    return ft.Container(
        content=content,
        padding=padding,
        bgcolor=SURFACE,
        border=ft.Border.all(1, BORDER),
        border_radius=20,
    )


def title(text: str, subtitle: str = "", action: ft.Control | None = None) -> ft.Row:
    heading = ft.Column(
        [ft.Text(text, size=26, weight=ft.FontWeight.BOLD, color=TEXT), ft.Text(subtitle, size=13, color=MUTED, visible=bool(subtitle))],
        spacing=2,
        tight=True,
        expand=True,
    )
    return ft.Row([heading, action] if action else [heading], vertical_alignment=ft.CrossAxisAlignment.CENTER)


def status_chip(status: str) -> ft.Container:
    color = STATUS_TONES.get(status, "#64748b")
    return ft.Container(
        ft.Text(STATUS_LABELS.get(status, status), size=11, color=ft.Colors.WHITE, weight=ft.FontWeight.W_700),
        padding=ft.Padding.symmetric(horizontal=9, vertical=5),
        bgcolor=color,
        border=ft.Border.all(1, color),
        border_radius=14,
    )


def empty(text: str) -> ft.Container:
    return ft.Container(
        ft.Column([ft.Icon(ft.Icons.INBOX_OUTLINED, size=34, color=MUTED), ft.Text(text, color=MUTED)], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        alignment=ft.Alignment.CENTER,
        padding=36,
    )


def data_table(headers: list[str], rows: list[list[ft.Control]], empty_text: str, *, width: int) -> ft.Control:
    if not rows:
        return card(empty(empty_text), padding=0)

    # Material DataTable sizes every column from its content, so a short data
    # set never occupies the available page width.  This flex-based table keeps
    # the same table semantics while giving each column a share of the row.
    def weight(header: str) -> int:
        if header == "จัดการ":
            return 18
        if header == "สถานะ":
            return 12
        if header == "ประเภท / สังกัด":
            return 24
        if header in {"วันที่ยืม / กำหนดคืน", "ยี่ห้อ / รุ่น"}:
            return 18
        if header in {"Asset code", "เลขรายการ", "Username"}:
            return 15
        return 20

    def table_row(cells: list[ft.Control], *, header: bool = False) -> ft.Container:
        def compact(cell: ft.Control) -> ft.Control:
            if not header and isinstance(cell, ft.Text):
                cell.max_lines = 1
                cell.overflow = ft.TextOverflow.ELLIPSIS
            return cell

        return ft.Container(
            ft.Row(
                [
                    ft.Container(
                        compact(cell),
                        expand=weight(headers[index]),
                        padding=ft.Padding.symmetric(horizontal=10, vertical=12 if header else 10),
                        alignment=ft.Alignment.CENTER_LEFT,
                    )
                    for index, cell in enumerate(cells)
                ],
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=SOFT if header else SURFACE,
            border=None if header else ft.Border.only(bottom=ft.BorderSide(1, BORDER)),
        )

    header_row = table_row(
        [ft.Text(label, size=13, weight=ft.FontWeight.W_600, color=MUTED) for label in headers],
        header=True,
    )
    table = ft.Container(
        ft.Column([header_row, *[table_row(row) for row in rows]], spacing=0),
        width=width,
    )
    return ft.Container(
        ft.Row([table], scroll=ft.ScrollMode.AUTO, width=float("inf")),
        width=float("inf"),
        bgcolor=SURFACE,
        border=ft.Border.all(1, BORDER),
        border_radius=16,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )


def row_action(icon, tooltip: str, on_click, *, visible: bool = True) -> ft.IconButton:
    return ft.IconButton(icon=icon, icon_size=18, tooltip=tooltip, visible=visible, on_click=on_click, width=32, height=32, padding=4)


def dropdown(label: str, rows, *, value: int | str | None = None, hint: str = "เลือก") -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        value=str(value) if value is not None else None,
        hint_text=hint,
        options=[ft.DropdownOption(key=str(row["id"]), text=str(row["name"])) for row in rows],
        border_radius=12,
        height=52,
        expand=True,
    )


class AppUI:
    def __init__(self, page: ft.Page, service: AppService | None = None) -> None:
        self.page = page
        self.service = service or AppService()
        self.messenger = LineMessenger()
        self.root = ft.Container(expand=True)
        self.user: User | None = None
        # Set only during the first successful LINE-link flow.  It lets the
        # user choose a new password without typing the just-verified initial
        # password a second time.  It is never persisted.
        self._line_verified_initial_password: str | None = None
        self.route = "dashboard"
        self.query = ""
        self.master_kind = "faculty"
        self.equipment_tab = "units"
        self.selected_borrower_id: int | None = None
        self.selected_unit_ids: set[int] = set()
        self.loan_equipment_query = ""
        self.loan_borrow_date = bangkok_today().isoformat()
        self.loan_due_date = (bangkok_today() + timedelta(days=7)).isoformat()
        self.pending_import: ImportPreview | None = None
        self.mobile = bool(self.page.width and self.page.width < 900)
        # FilePicker event handlers must be present when the service is mounted.
        # Assigning on_result only when the dialog opens leaves the web client
        # without a result subscription, so selecting a file appears to do
        # nothing (notably in Safari).
        self.file_picker = ft.FilePicker(on_result=self._handle_import_file_selected)
        self.preferences = ft.SharedPreferences()
        self.page.services.append(self.file_picker)
        self.page.services.append(self.preferences)
        self.page.add(self.root)
        self.page.on_login = self._line_authorized
        self.page.on_resize = self._resize
        stored = self.page.session.store.get("user_id")
        self.user = self.service.get_user(stored)
        if self.user and self.user.status != "active":
            self.user = None
        self.render()
        if self.user is None:
            self.page.run_task(self._restore_persistent_login)
        self.page.run_task(self._reminder_loop)

    def _resize(self, event) -> None:
        mobile = bool(event.width and event.width < 900)
        if mobile != self.mobile:
            self.mobile = mobile
            self.render()

    def feedback(self, message: str, *, error: bool = False) -> None:
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message, color=ft.Colors.WHITE),
                bgcolor=DANGER if error else SUCCESS,
                show_close_icon=True,
            )
        )

    def close_dialog(self) -> None:
        try:
            self.page.pop_dialog()
        except Exception:
            pass

    def dialog(self, heading: str, content: ft.Control, save_text: str, on_save=None, *, width: int = 620, action=None) -> None:
        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(heading, size=20, weight=ft.FontWeight.BOLD),
                content=ft.Container(content, width=width),
                actions=[
                    ft.TextButton("ยกเลิก", on_click=lambda _: self.close_dialog()),
                    ft.Button(save_text, bgcolor=PRIMARY, color=ft.Colors.WHITE, on_click=on_save, action=action),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
                shape=ft.RoundedRectangleBorder(radius=20),
                scrollable=True,
            )
        )

    def confirm(self, heading: str, message: str, action_text: str, action) -> None:
        self.dialog(heading, ft.Text(message), action_text, action, width=420)

    def render(self) -> None:
        if self.user is None:
            self.root.content = self.login_screen()
        elif self.user.must_change_password:
            self.root.content = self.password_screen(forced=True)
        else:
            self.root.content = self.shell()
        self.page.update()

    def login_screen(self) -> ft.Control:
        username = ft.TextField(label="ชื่อผู้ใช้", autofocus=True, border_radius=12, height=52)
        password = ft.TextField(label="รหัสผ่าน", password=True, can_reveal_password=True, border_radius=12, height=52, on_submit=lambda _: submit(None))
        message = ft.Text("", color=DANGER, size=13)

        def submit(_):
            try:
                self.login(self.service.authenticate(username.value or "", password.value or ""))
            except AppError as error:
                message.value = str(error)
                message.update()

        form = card(
            ft.Column(
                [
                    ft.Text("เข้าสู่ระบบ", size=30, weight=ft.FontWeight.BOLD, color=TEXT),
                    ft.Text("ระบบยืม–คืนอุปกรณ์ สาขาวิทยาการคอมพิวเตอร์", color=MUTED),
                    username,
                    password,
                    message,
                    ft.Button("เข้าสู่ระบบ", icon=ft.Icons.LOGIN, height=48, bgcolor=PRIMARY, color=ft.Colors.WHITE, on_click=submit),
                    ft.Row([ft.Divider(expand=True), ft.Text("หรือ", color=MUTED), ft.Divider(expand=True)]),
                    ft.OutlinedButton("เข้าสู่ระบบด้วย LINE", icon=ft.Icons.CHAT_BUBBLE_OUTLINE, height=48, on_click=lambda _: self.start_line_login()),
                    ft.Text("ผู้ใช้ใหม่ต้องเปลี่ยนรหัสผ่านก่อนเริ่มใช้งาน", size=12, color=MUTED),
                ],
                spacing=16,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                tight=True,
            )
        )
        form.width = 440
        form.height = 500
        return ft.Container(
            ft.Row([form], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER, expand=True),
            padding=24,
            bgcolor=CANVAS,
            expand=True,
        )

    async def _restore_persistent_login(self) -> None:
        token = await self.preferences.get("auth_token")
        user = self.service.user_for_session(token if isinstance(token, str) else None)
        if user is None:
            if token is not None:
                await self.preferences.remove("auth_token")
            return
        self.user = user
        self.page.session.store.set("user_id", user.id)
        self.route = "dashboard"
        self.render()

    async def _persist_login(self, user_id: int) -> None:
        if self.user is None or self.user.id != user_id:
            return
        previous = await self.preferences.get("auth_token")
        if isinstance(previous, str):
            self.service.revoke_session(previous)
        token = self.service.create_session(user_id)
        if self.user is not None and self.user.id == user_id:
            await self.preferences.set("auth_token", token)
        else:
            self.service.revoke_session(token)

    async def _clear_persistent_login(self) -> None:
        token = await self.preferences.get("auth_token")
        self.service.revoke_session(token if isinstance(token, str) else None)
        await self.preferences.remove("auth_token")

    def login(self, user: User) -> None:
        self.user = user
        self.page.session.store.set("user_id", user.id)
        self.route = "dashboard"
        self.render()
        self.page.run_task(self._persist_login, user.id)

    def logout(self) -> None:
        self.user = None
        self._line_verified_initial_password = None
        self.page.session.store.remove("user_id")
        self.render()
        self.page.run_task(self._clear_persistent_login)

    def start_line_login(self) -> None:
        line_provider = provider()
        if line_provider is None:
            self.feedback("ยังไม่ได้ตั้งค่า LINE_CLIENT_ID, LINE_CLIENT_SECRET และ LINE_REDIRECT_URL", error=True)
            return

        async def open_url(url: str) -> None:
            await UrlLauncher().launch_url(url, web_only_window_name="_self")

        self.page.run_task(self.page.login, line_provider, redirect_to_page=True, on_open_authorization_url=open_url)

    def _line_authorized(self, event: ft.LoginEvent) -> None:
        if event.error or self.page.auth is None or self.page.auth.user is None:
            self.feedback("LINE Login ไม่สำเร็จ กรุณาตรวจ Redirect URL แล้วลองใหม่", error=True)
            return
        line_user_id = self.page.auth.user.id
        existing = self.service.find_by_line(line_user_id)
        if existing:
            self.login(existing)
            return
        self.line_link_dialog(line_user_id)

    def line_link_dialog(self, line_user_id: str) -> None:
        username = ft.TextField(label="ชื่อผู้ใช้ของระบบ", value=self.user.username if self.user else "")
        password = ft.TextField(label="รหัสผ่านของระบบ", password=True, can_reveal_password=True)

        def link(_):
            try:
                verified_password = password.value or ""
                user = self.service.link_line(username.value or "", verified_password, line_user_id)
                self.close_dialog()
                if user.must_change_password:
                    self._line_verified_initial_password = verified_password
                self.login(user)
                self.feedback("เชื่อมบัญชี LINE แล้ว กรุณาตั้งรหัสผ่านใหม่")
            except AppError as error:
                self.feedback(str(error), error=True)

        self.dialog(
            "เชื่อม LINE กับบัญชีระบบ",
            ft.Column([ft.Text("ยืนยันชื่อผู้ใช้และรหัสผ่านครั้งเดียว เพื่อป้องกันการผูกผิดคน", color=MUTED), username, password], spacing=14, tight=True),
            "เชื่อมบัญชี",
            link,
        )

    def password_screen(self, *, forced: bool = False) -> ft.Control:
        current = ft.TextField(label="รหัสผ่านปัจจุบัน", password=True, can_reveal_password=True)
        new = ft.TextField(label="รหัสผ่านใหม่ อย่างน้อย 8 ตัว", password=True, can_reveal_password=True)
        confirm = ft.TextField(label="ยืนยันรหัสผ่านใหม่", password=True, can_reveal_password=True)
        message = ft.Text("", color=DANGER)
        verified_initial_password = self._line_verified_initial_password if forced else None

        def save(_):
            if new.value != confirm.value:
                message.value = "รหัสผ่านใหม่ไม่ตรงกัน"
                message.update()
                return
            try:
                self.user = self.service.change_password(  # type: ignore[union-attr]
                    self.user.id,
                    verified_initial_password if verified_initial_password is not None else current.value or "",
                    new.value or "",
                )
                self._line_verified_initial_password = None
                self.page.run_task(self._persist_login, self.user.id)
                self.feedback("เปลี่ยนรหัสผ่านแล้ว")
                self.render()
            except AppError as error:
                message.value = str(error)
                message.update()

        content = card(
            ft.Column(
                [
                    ft.Text("ตั้งรหัสผ่านใหม่" if forced else "เปลี่ยนรหัสผ่าน", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "ยืนยันบัญชีผ่าน LINE แล้ว กรุณาตั้งรหัสผ่านใหม่ก่อนเริ่มใช้งาน"
                        if verified_initial_password is not None
                        else "ต้องเปลี่ยนรหัสผ่านก่อนใช้งานครั้งแรก"
                        if forced
                        else "ใช้รหัสผ่านที่จำง่ายสำหรับคุณและเดายากสำหรับผู้อื่น",
                        color=MUTED,
                    ),
                    *([] if verified_initial_password is not None else [current]),
                    new,
                    confirm,
                    message,
                    ft.Button("บันทึกรหัสผ่าน", bgcolor=PRIMARY, color=ft.Colors.WHITE, height=48, on_click=save),
                    ft.TextButton("ออกจากระบบ", visible=forced, on_click=lambda _: self.logout()),
                ],
                spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            )
        )
        return ft.Container(content, width=520, alignment=ft.Alignment.CENTER, padding=24, bgcolor=CANVAS, expand=True)

    def navigation(self):
        if self.user.role == "admin":  # type: ignore[union-attr]
            return [
                ("dashboard", "ภาพรวม", ft.Icons.DASHBOARD_OUTLINED),
                ("loans", "ยืม–คืน", ft.Icons.SWAP_HORIZ),
                ("users", "ผู้ใช้", ft.Icons.PEOPLE_OUTLINED),
                ("equipment", "อุปกรณ์", ft.Icons.INVENTORY_2_OUTLINED),
                ("masters", "ข้อมูลอ้างอิง", ft.Icons.ACCOUNT_TREE_OUTLINED),
                ("history", "ประวัติ", ft.Icons.HISTORY),
                ("account", "บัญชี", ft.Icons.PERSON_OUTLINE),
            ]
        return [
            ("dashboard", "หน้าหลัก", ft.Icons.HOME_OUTLINED),
            ("my_loans", "ของที่ยืม", ft.Icons.ASSIGNMENT_OUTLINED),
            ("available", "อุปกรณ์", ft.Icons.INVENTORY_2_OUTLINED),
            ("history", "ประวัติ", ft.Icons.HISTORY),
            ("account", "บัญชี", ft.Icons.PERSON_OUTLINE),
        ]

    def go(self, route: str) -> None:
        self.route = route
        self.query = ""
        self.render()

    def shell(self) -> ft.Control:
        items = self.navigation()
        allowed_routes = {item[0] for item in items} | ({"new_loan"} if self.user.role == "admin" else set())  # type: ignore[union-attr]
        if self.route not in allowed_routes:
            self.route = items[0][0]
        nav_route = "loans" if self.route == "new_loan" else self.route
        content = ft.Container(self.route_content(), padding=20 if self.mobile else 32, bgcolor=CANVAS, expand=True)
        if self.mobile:
            page_selector = ft.Dropdown(
                value=nav_route,
                options=[ft.DropdownOption(key=route, text=label) for route, label, _ in items],
                on_select=lambda event: self.go(event.control.value),
                width=180,
                dense=True,
            )
            mobile_header = ft.Container(
                ft.Row(
                    [
                        ft.Text("LAB LENDING", weight=ft.FontWeight.BOLD, color=PRIMARY, expand=True),
                        page_selector,
                        ft.IconButton(icon=ft.Icons.LOGOUT, tooltip="ออกจากระบบ", on_click=lambda _: self.logout()),
                    ]
                ),
                padding=ft.Padding.symmetric(horizontal=20, vertical=10),
                bgcolor=SURFACE,
                border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)),
            )
            return ft.Column([mobile_header, content], spacing=0, expand=True)
        sidebar = ft.Container(
            ft.Column(
                [
                    ft.Container(
                        ft.Row(
                            [
                                ft.Container(ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, color=PRIMARY), padding=10, bgcolor="#eaf2ff", border_radius=12),
                                ft.Column([ft.Text("LAB LENDING", weight=ft.FontWeight.BOLD, color=TEXT), ft.Text("EQUIPMENT SYSTEM", size=10, color=MUTED)], spacing=1),
                            ],
                            spacing=10,
                        ),
                        padding=ft.Padding.only(left=8, right=8, top=10, bottom=18),
                    ),
                    *[
                        ft.TextButton(
                            label,
                            icon=icon,
                            height=48,
                            width=float("inf"),
                            style=ft.ButtonStyle(
                                bgcolor="#eaf2ff" if route == nav_route else ft.Colors.TRANSPARENT,
                                color=PRIMARY if route == nav_route else TEXT,
                                icon_color=PRIMARY if route == nav_route else TEXT,
                                shape=ft.RoundedRectangleBorder(radius=10),
                                alignment=ft.Alignment.CENTER_LEFT,
                                overlay_color={ft.ControlState.HOVERED: "#f4f7fb"},
                            ),
                            on_click=lambda _, target=route: self.go(target),
                        )
                        for route, label, icon in items
                    ],
                    ft.Container(expand=True),
                    ft.Container(
                        ft.Row(
                            [
                                ft.CircleAvatar(content=ft.Text(self.user.full_name[:1]), bgcolor="#eaf2ff", color=PRIMARY),
                                ft.Column([ft.Text(self.user.full_name, size=13, weight=ft.FontWeight.W_600), ft.Text(ROLE_LABELS[self.user.role], size=11, color=MUTED)], spacing=1, expand=True),
                                row_action(ft.Icons.LOGOUT, "ออกจากระบบ", lambda _: self.logout()),
                            ]
                        ),
                        padding=8,
                        border=ft.Border.only(top=ft.BorderSide(1, BORDER)),
                    ),
                ],
                spacing=4,
                expand=True,
            ),
            width=260,
            padding=12,
            bgcolor=SURFACE,
            border=ft.Border.only(right=ft.BorderSide(1, BORDER)),
        )
        return ft.Row([sidebar, content], spacing=0, expand=True)

    def route_content(self) -> ft.Control:
        return {
            "dashboard": self.dashboard_view,
            "loans": self.loan_workspace,
            "new_loan": self.new_loan_view,
            "users": self.users_view,
            "equipment": self.equipment_view,
            "masters": self.master_view,
            "history": self.history_view,
            "my_loans": self.my_loans_view,
            "available": self.available_view,
            "account": self.account_view,
        }[self.route]()

    def dashboard_view(self) -> ft.Control:
        metrics = self.service.dashboard(self.user)  # type: ignore[arg-type]
        definitions = (
            [("กำลังยืม", metrics["active"]), ("เกินกำหนด", metrics["overdue"]), ("ครบกำหนดวันนี้", metrics["due_today"]), ("คืนวันนี้", metrics["returned_today"]), ("พร้อมยืม", metrics["available"])]
            if self.user.role == "admin"  # type: ignore[union-attr]
            else [("รายการของฉัน", metrics["active"]), ("เกินกำหนด", metrics["overdue"]), ("อุปกรณ์พร้อมยืม", metrics["available"])]
        )
        cards = ft.ResponsiveRow(
            [card(ft.Column([ft.Text(label, color=MUTED), ft.Text(str(value), size=30, weight=ft.FontWeight.BOLD, color=DANGER if label == "เกินกำหนด" and value else TEXT)], spacing=4), padding=16) for label, value in definitions],
            columns=12,
            spacing=12,
        )
        for item in cards.controls:
            item.col = {"xs": 6, "md": 4, "lg": 2.4 if self.user.role == "admin" else 4}  # type: ignore[union-attr]
        loans = self.service.list_loans(status="active", borrower_id=None if self.user.role == "admin" else self.user.id)  # type: ignore[union-attr]
        return ft.Column(
            [title("ภาพรวม", "งานและรายการสำคัญวันนี้"), cards, ft.Text("รายการที่กำลังยืม", size=18, weight=ft.FontWeight.BOLD), self.loan_cards(loans[:8])],
            spacing=18,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def search_bar(self, hint: str, action) -> ft.Row:
        field = ft.TextField(value=self.query, hint_text=hint, prefix_icon=ft.Icons.SEARCH, expand=True, height=48, border_radius=12, on_submit=lambda _: action(field.value or ""))
        return ft.Container(
            ft.Row([field, ft.Button("ค้นหา", icon=ft.Icons.SEARCH, height=44, on_click=lambda _: action(field.value or ""))]),
            padding=12,
            bgcolor=SURFACE,
            border=ft.Border.all(1, BORDER),
            border_radius=16,
        )

    def set_query(self, value: str) -> None:
        self.query = value.strip()
        self.render()

    def table(self, headers: list[str], rows: list[list[ft.Control]], empty_text: str) -> ft.Control:
        viewport = int(self.page.width or 1280)
        content_width = viewport - (48 if self.mobile else 324)
        minimum_width = max(640, len(headers) * 120)
        return data_table(headers, rows, empty_text, width=max(content_width, minimum_width))

    def loan_cards(self, loans) -> ft.Control:
        today = bangkok_today().isoformat()
        rows = []
        for loan in loans:
            overdue = loan["status"] == "active" and loan["due_date"] < today
            rows.append(
                [
                    ft.Text(loan["code"], weight=ft.FontWeight.W_600),
                    ft.Column([ft.Text(loan["full_name"], weight=ft.FontWeight.W_600), ft.Text(f"@{loan['username']}", size=12, color=MUTED)], spacing=1),
                    ft.Text(f"{loan['item_count']} ชิ้น · คงค้าง {loan['outstanding_count']}"),
                    ft.Column([ft.Text(loan["borrow_date"]), ft.Text(f"ถึง {loan['due_date']}", size=12, color=DANGER if overdue else MUTED)], spacing=1),
                    status_chip("overdue" if overdue else loan["status"]),
                    ft.Row(
                        [
                            row_action(ft.Icons.ASSIGNMENT_RETURN_OUTLINED, "รับคืน", lambda _, item=loan: self.return_dialog(item), visible=self.user.role == "admin" and loan["status"] == "active"),  # type: ignore[union-attr]
                            row_action(ft.Icons.VISIBILITY_OUTLINED, "รายละเอียด", lambda _, item=loan: self.loan_detail(item)),
                        ],
                        spacing=0,
                    ),
                ]
            )
        return self.table(["เลขรายการ", "ผู้ยืม", "อุปกรณ์", "วันที่ยืม / กำหนดคืน", "สถานะ", "จัดการ"], rows, "ยังไม่มีรายการ")

    def loan_detail(self, loan) -> None:
        items = self.service.loan_items(loan["id"])
        rows = [ft.Row([ft.Text(item["asset_code"], weight=ft.FontWeight.BOLD, expand=True), ft.Text(item["type_name"], expand=True), status_chip("completed" if item["returned_at"] else "borrowed")]) for item in items]
        self.dialog(f"รายละเอียด {loan['code']}", ft.Column(rows or [empty("ไม่มีอุปกรณ์")], spacing=10), "ปิด", lambda _: self.close_dialog())

    def history_view(self) -> ft.Control:
        loans = self.service.list_loans(self.query, borrower_id=None if self.user.role == "admin" else self.user.id)  # type: ignore[union-attr]
        return ft.Column(
            [title("ประวัติการยืม–คืน", "ค้นหาด้วยรหัสรายการ ชื่อผู้ใช้ หรือชื่อผู้ยืม"), self.search_bar("ค้นหาประวัติ", self.set_query), self.loan_cards(loans)],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def my_loans_view(self) -> ft.Control:
        loans = self.service.list_loans(status="active", borrower_id=self.user.id)  # type: ignore[union-attr]
        return ft.Column([title("ของที่กำลังยืม", "ตรวจวันครบกำหนดและรายการคงค้างของคุณ"), self.loan_cards(loans)], spacing=16, expand=True, scroll=ft.ScrollMode.AUTO)

    def available_view(self) -> ft.Control:
        units = self.service.list_units(self.query, "available")
        rows = [[ft.Text(row["asset_code"], weight=ft.FontWeight.W_600), ft.Text(row["type_name"]), ft.Text(row["category_name"]), ft.Text(row["storage_location"]), status_chip("available")] for row in units]
        return ft.Column([title("อุปกรณ์พร้อมยืม", "ดูรายการได้ แต่การยืมต้องให้ผู้ดูแลเป็นผู้ทำรายการ"), self.search_bar("ค้นหาชื่อหรือ asset code", self.set_query), self.table(["Asset code", "ชนิดอุปกรณ์", "หมวดหมู่", "ตำแหน่ง", "สถานะ"], rows, "ไม่พบอุปกรณ์พร้อมยืม")], spacing=16, expand=True, scroll=ft.ScrollMode.AUTO)

    async def _reminder_loop(self) -> None:
        while True:
            for message in self.service.claim_due_reminders():
                self.messenger.send(message)
            await asyncio.sleep(86_400)

    def loan_workspace(self) -> ft.Control:
        active_loans = self.service.list_loans(self.query, status="active")
        action = ft.Button("ทำรายการยืม", icon=ft.Icons.ADD, bgcolor=PRIMARY, color=ft.Colors.WHITE, height=44, on_click=lambda _: self.go("new_loan"))
        return ft.Column(
            [title("รายการยืม–คืน", "ค้นหารายการที่กำลังยืมและรับคืนอุปกรณ์", action), self.search_bar("ค้นหาเลขรายการ ชื่อ หรือ username", self.set_query), self.loan_cards(active_loans)],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def new_loan_view(self) -> ft.Control:
        borrowers = [row for row in self.service.list_users(status="active") if row["role"] == "borrower"]
        borrower_by_id = {row["id"]: row for row in borrowers}
        all_units = self.service.list_units(status="available")
        available_units = self.service.list_units(self.loan_equipment_query, "available")
        today = bangkok_today()
        borrower = ft.Dropdown(
            label="ผู้ยืม *",
            value=str(self.selected_borrower_id) if self.selected_borrower_id else None,
            options=[ft.DropdownOption(key=str(row["id"]), text=f"{row['full_name']} (@{row['username']})") for row in borrowers],
            editable=True,
            enable_filter=True,
            enable_search=True,
            leading_icon=ft.Icons.PERSON_SEARCH_OUTLINED,
            hint_text="พิมพ์ชื่อหรือ username",
            height=52,
            border_radius=12,
            on_select=lambda event: setattr(self, "selected_borrower_id", int(event.control.value) if event.control.value else None),
        )
        borrow_date = ft.TextField(
            label="วันยืม (YYYY-MM-DD)",
            value=self.loan_borrow_date,
            width=240,
            on_change=lambda event: setattr(self, "loan_borrow_date", event.control.value or ""),
        )
        due_date = ft.TextField(
            label="วันครบกำหนด (YYYY-MM-DD)",
            value=self.loan_due_date,
            width=240,
            on_change=lambda event: setattr(self, "loan_due_date", event.control.value or ""),
        )
        selected_text = ft.Text(f"เลือกแล้ว {len(self.selected_unit_ids)} ชิ้น", color=PRIMARY, weight=ft.FontWeight.W_600)

        def toggle_unit(unit_id: int, selected: bool) -> None:
            if selected:
                self.selected_unit_ids.add(unit_id)
            else:
                self.selected_unit_ids.discard(unit_id)
            selected_text.value = f"เลือกแล้ว {len(self.selected_unit_ids)} ชิ้น"
            selected_text.update()

        unit_search = ft.TextField(
            value=self.loan_equipment_query,
            hint_text="ค้นหา asset code ชื่อ ยี่ห้อ รุ่น หรือตำแหน่ง",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            height=48,
            border_radius=12,
        )

        def filter_units(_):
            self.loan_equipment_query = (unit_search.value or "").strip()
            self.render()

        def request_create(_):
            try:
                start = date.fromisoformat(borrow_date.value or "")
                due = date.fromisoformat(due_date.value or "")
            except ValueError:
                self.feedback("กรุณากรอกวันที่เป็น YYYY-MM-DD", error=True)
                return
            selected_borrower = borrower_by_id.get(self.selected_borrower_id)
            borrower_name = selected_borrower["full_name"] if selected_borrower else "ยังไม่ได้เลือก"
            self.confirm(
                "ยืนยันการยืม",
                f"ผู้ยืม: {borrower_name}\nอุปกรณ์: {len(self.selected_unit_ids)} ชิ้น\nครบกำหนด: {due}",
                "ยืนยันการยืม",
                lambda event: create(event, start, due),
            )

        def create(_, start: date, due: date):
            try:
                loan = self.service.create_loan(self.user.id, self.selected_borrower_id or 0, list(self.selected_unit_ids), start, due)  # type: ignore[union-attr]
                self.close_dialog()
                if loan["line_user_id"]:
                    self.messenger.send(LineMessage(loan["line_user_id"], f"ยืมสำเร็จ: {loan['code']} จำนวน {loan['item_count']} ชิ้น กำหนดคืน {loan['due_date']}"))
                self.selected_borrower_id = None
                self.selected_unit_ids.clear()
                self.loan_equipment_query = ""
                self.loan_borrow_date = bangkok_today().isoformat()
                self.loan_due_date = (bangkok_today() + timedelta(days=7)).isoformat()
                self.route = "loans"
                self.feedback(f"บันทึกรายการ {loan['code']} แล้ว")
                self.render()
            except (AppError, ValueError) as error:
                self.close_dialog()
                self.feedback(str(error), error=True)

        unit_rows = []
        for row in available_units:
            brand_model = " · ".join(part for part in (row["brand"], row["model"]) if part) or "ไม่ระบุยี่ห้อ/รุ่น"
            unit_rows.append(
                ft.Container(
                    ft.Checkbox(
                        label=f"{row['type_name']} — {brand_model}\n{row['asset_code']} · {row['storage_location']}",
                        value=row["id"] in self.selected_unit_ids,
                        on_change=lambda event, unit_id=row["id"]: toggle_unit(unit_id, bool(event.control.value)),
                    ),
                    padding=ft.Padding.symmetric(horizontal=4, vertical=2),
                )
            )
        create_panel = card(
            ft.Column(
                [
                    ft.Text("1. เลือกผู้ยืม", size=18, weight=ft.FontWeight.BOLD),
                    borrower,
                    ft.Text("2. เลือกอุปกรณ์", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([unit_search, ft.Button("ค้นหา", icon=ft.Icons.SEARCH, height=44, on_click=filter_units)]),
                    ft.Row([ft.Text(f"พบ {len(available_units)} จาก {len(all_units)} ชิ้น", color=MUTED, expand=True), selected_text]),
                    ft.Container(
                        ft.Column(unit_rows, spacing=0, scroll=ft.ScrollMode.AUTO) if unit_rows else empty("ไม่พบอุปกรณ์พร้อมยืม"),
                        height=280,
                        padding=12,
                        border=ft.Border.all(1, BORDER),
                        border_radius=12,
                        bgcolor=SURFACE,
                    ),
                    ft.Text("3. กำหนดวันคืน", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([borrow_date, due_date], wrap=True),
                    ft.Row(
                        [
                            ft.OutlinedButton("+3 วัน", on_click=lambda _: self._set_loan_due_date(due_date, today + timedelta(days=3))),
                            ft.OutlinedButton("+7 วัน", on_click=lambda _: self._set_loan_due_date(due_date, today + timedelta(days=7))),
                            ft.OutlinedButton("+14 วัน", on_click=lambda _: self._set_loan_due_date(due_date, today + timedelta(days=14))),
                        ],
                        wrap=True,
                    ),
                    ft.Row(
                        [
                            ft.OutlinedButton("ยกเลิก", icon=ft.Icons.ARROW_BACK, on_click=lambda _: self.go("loans")),
                            ft.Button("ตรวจสอบและยืนยัน", icon=ft.Icons.CHECK_CIRCLE_OUTLINE, bgcolor=PRIMARY, color=ft.Colors.WHITE, height=48, on_click=request_create),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=12,
            )
        )
        return ft.Column(
            [title("ทำรายการยืมใหม่", "เลือกผู้ยืมและอุปกรณ์หลายชิ้นในรายการเดียว"), create_panel],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    def _set_loan_due_date(self, field: ft.TextField, value: date) -> None:
        self.loan_due_date = value.isoformat()
        field.value = value.isoformat()
        field.update()

    def return_dialog(self, loan) -> None:
        items = self.service.loan_items(loan["id"], outstanding_only=True)
        selected = {row["id"] for row in items}

        def toggle(item_id: int, checked: bool):
            if checked:
                selected.add(item_id)
            else:
                selected.discard(item_id)

        def ask(_):
            if not selected:
                self.feedback("กรุณาเลือกอุปกรณ์ที่รับคืน", error=True)
                return
            self.close_dialog()
            self.confirm(
                "ยืนยันรับคืน",
                f"รับคืน {len(selected)} จาก {len(items)} ชิ้นในรายการ {loan['code']}",
                "ยืนยันรับคืน",
                submit,
            )

        def submit(_):
            try:
                result = self.service.return_items(self.user.id, loan["id"], list(selected))  # type: ignore[union-attr]
                self.close_dialog()
                if result["outstanding_count"] == 0 and result["line_user_id"]:
                    self.messenger.send(LineMessage(result["line_user_id"], f"คืนอุปกรณ์ครบแล้ว: {result['code']} จำนวน {result['item_count']} ชิ้น"))
                self.feedback("บันทึกรับคืนแล้ว" if result["outstanding_count"] else "รับคืนครบและปิดรายการแล้ว")
                self.render()
            except AppError as error:
                self.close_dialog()
                self.feedback(str(error), error=True)

        controls = [
            ft.Checkbox(
                label=f"{row['asset_code']} · {row['type_name']}",
                value=True,
                on_change=lambda event, item_id=row["id"]: toggle(item_id, bool(event.control.value)),
            )
            for row in items
        ]
        self.dialog(f"รับคืน {loan['code']}", ft.Column([ft.Text("เลือกเฉพาะชิ้นที่รับคืนครั้งนี้", color=MUTED), *controls], spacing=8), "ดำเนินการต่อ", ask)

    def users_view(self) -> ft.Control:
        rows = self.service.list_users(self.query)
        actions = ft.Row(
            [
                ft.OutlinedButton("Import", icon=ft.Icons.UPLOAD_FILE, on_click=lambda _: self.import_users_dialog()),
                ft.Button("เพิ่มผู้ใช้", icon=ft.Icons.PERSON_ADD_OUTLINED, bgcolor=PRIMARY, color=ft.Colors.WHITE, on_click=lambda _: self.user_dialog()),
            ],
            wrap=True,
        )
        table_rows = []
        for row in rows:
            affiliation = [row["department_name"], row["cohort_name"], row["class_group_name"]]
            details = " · ".join(value for value in [TYPE_LABELS.get(row["user_type"], row["user_type"]), *affiliation] if value)
            if not details:
                details = row["faculty_name"] or "ไม่ระบุข้อมูล"
            table_rows.append(
                [
                    ft.Row([ft.CircleAvatar(content=ft.Text(row["full_name"][:1]), bgcolor="#eaf2ff", color=PRIMARY, radius=18), ft.Text(row["full_name"], weight=ft.FontWeight.W_600)], spacing=10),
                    ft.Text(f"@{row['username']}"),
                    ft.Text(ROLE_LABELS[row["role"]]),
                    ft.Text(details, size=12, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    status_chip(row["status"]),
                    ft.Row(
                        [
                            row_action(ft.Icons.HISTORY, "ประวัติ", lambda _, user_id=row["id"], name=row["full_name"]: self.user_history_dialog(user_id, name), visible=row["role"] == "borrower"),
                            row_action(ft.Icons.LOCK_RESET, "รีเซ็ตรหัส", lambda _, item=row: self.reset_password_dialog(item)),
                            row_action(ft.Icons.EDIT_OUTLINED, "แก้ไข", lambda _, item=row: self.user_dialog(item)),
                            row_action(ft.Icons.BLOCK if row["status"] == "active" else ft.Icons.CHECK_CIRCLE_OUTLINE, "ปิดใช้งาน" if row["status"] == "active" else "เปิดใช้งาน", lambda _, item=row: self.user_status_dialog(item)),
                        ],
                        spacing=0,
                    ),
                ]
            )
        return ft.Column([title("ผู้ใช้", "สร้าง แก้ไข ปิดใช้งาน รีเซ็ตรหัส และ import", actions), self.search_bar("ค้นหาชื่อหรือ username", self.set_query), self.table(["ชื่อ", "Username", "บทบาท", "ประเภท / สังกัด", "สถานะ", "จัดการ"], table_rows, "ไม่พบผู้ใช้")], spacing=16, expand=True, scroll=ft.ScrollMode.AUTO)

    def user_dialog(self, row=None) -> None:
        username = ft.TextField(label="Username *", value=row["username"] if row else "")
        full_name = ft.TextField(label="ชื่อ–นามสกุล *", value=row["full_name"] if row else "")
        email = ft.TextField(label="อีเมลสำรอง", value=(row["backup_email"] or "") if row else "")
        role = ft.Dropdown(label="บทบาท", value=row["role"] if row else "borrower", options=[ft.DropdownOption("borrower", "ผู้ยืม"), ft.DropdownOption("admin", "ผู้ดูแลระบบ")])
        user_type = ft.Dropdown(label="ประเภทผู้ใช้", value=row["user_type"] if row else "student", options=[ft.DropdownOption(key=key, text=value) for key, value in TYPE_LABELS.items()])
        faculties = self.service.list_master("faculty", active_only=True)
        departments = self.service.list_master("department", active_only=True)
        cohorts = self.service.list_master("cohort", active_only=True)
        groups = self.service.list_master("class_group", active_only=True)
        faculty_value = row["faculty_id"] if row else None
        department_value = row["department_id"] if row else None
        cohort_value = row["cohort_id"] if row else None
        faculty = dropdown("คณะ", faculties, value=faculty_value)
        department = dropdown("สาขา", [item for item in departments if item["faculty_id"] == faculty_value], value=department_value)
        cohort = dropdown("รุ่น", [item for item in cohorts if item["department_id"] == department_value], value=cohort_value)
        class_group = dropdown("หมู่เรียน", [item for item in groups if item["cohort_id"] == cohort_value], value=row["class_group_id"] if row else None)
        student_fields = ft.Row([cohort, class_group], visible=(user_type.value == "student"))
        affiliation = ft.Column([ft.Text("สังกัดของผู้ยืม", weight=ft.FontWeight.BOLD), faculty, department, student_fields], spacing=12, visible=(role.value == "borrower"))

        def replace_options(field: ft.Dropdown, records) -> None:
            field.value = None
            field.options = [ft.DropdownOption(key=str(item["id"]), text=str(item["name"])) for item in records]
            field.update()

        def faculty_changed(_):
            replace_options(department, [item for item in departments if str(item["faculty_id"]) == faculty.value])
            replace_options(cohort, [])
            replace_options(class_group, [])

        def department_changed(_):
            replace_options(cohort, [item for item in cohorts if str(item["department_id"]) == department.value])
            replace_options(class_group, [])

        def cohort_changed(_):
            replace_options(class_group, [item for item in groups if str(item["cohort_id"]) == cohort.value])

        def role_changed(_):
            affiliation.visible = role.value == "borrower"
            affiliation.update()

        def type_changed(_):
            student_fields.visible = user_type.value == "student"
            student_fields.update()

        faculty.on_select = faculty_changed
        department.on_select = department_changed
        cohort.on_select = cohort_changed
        role.on_select = role_changed
        user_type.on_select = type_changed

        def optional_id(field: ft.Dropdown) -> int | None:
            return int(field.value) if field.value else None

        def save(_):
            try:
                self.service.save_user(
                    self.user.id,  # type: ignore[union-attr]
                    user_id=row["id"] if row else None,
                    username=username.value or "",
                    full_name=full_name.value or "",
                    backup_email=email.value or None,
                    role=role.value or "borrower",
                    user_type=user_type.value or "student",
                    faculty_id=optional_id(faculty),
                    department_id=optional_id(department),
                    cohort_id=optional_id(cohort),
                    class_group_id=optional_id(class_group),
                )
                self.close_dialog()
                self.feedback("บันทึกผู้ใช้แล้ว" + ("" if row else " รหัสผ่านเริ่มต้นคือ username"))
                self.render()
            except AppError as error:
                self.feedback(str(error), error=True)

        self.dialog(
            "แก้ไขผู้ใช้" if row else "เพิ่มผู้ใช้",
            ft.Column([username, ft.Text("3–50 ตัว: อังกฤษ ตัวเลข . _ -", size=12, color=MUTED), full_name, email, ft.Row([role, user_type]), affiliation], spacing=12, tight=True),
            "บันทึก",
            save,
        )

    def user_status_dialog(self, row) -> None:
        new_status = "inactive" if row["status"] == "active" else "active"

        def save(_):
            try:
                self.service.set_user_status(self.user.id, row["id"], new_status)  # type: ignore[union-attr]
                self.close_dialog()
                self.feedback("เปลี่ยนสถานะผู้ใช้แล้ว")
                self.render()
            except AppError as error:
                self.close_dialog()
                self.feedback(str(error), error=True)

        self.confirm("ยืนยันเปลี่ยนสถานะ", f"ต้องการ{STATUS_LABELS[new_status]}บัญชี {row['username']} ใช่หรือไม่", "ยืนยัน", save)

    def reset_password_dialog(self, row) -> None:
        def reset(_):
            try:
                password = self.service.reset_password(self.user.id, row["id"])  # type: ignore[union-attr]
                self.close_dialog()
                self.feedback(f"รีเซ็ตแล้ว รหัสผ่านชั่วคราวคือ {password}")
            except AppError as error:
                self.close_dialog()
                self.feedback(str(error), error=True)

        self.confirm("รีเซ็ตรหัสผ่าน", f"รหัสผ่านจะกลับเป็น username: {row['username']} และบังคับเปลี่ยนเมื่อเข้าสู่ระบบ", "รีเซ็ต", reset)

    def user_history_dialog(self, user_id: int, name: str) -> None:
        loans = self.service.user_history(user_id)
        self.dialog(f"ประวัติของ {name}", self.loan_cards(loans), "ปิด", lambda _: self.close_dialog())

    def _handle_import_file_selected(self, event: ft.FilePickerResultEvent) -> None:
        files = event.files
        if not files:
            return
        selected_file = files[0]
        try:
            data = selected_file.bytes
            if isinstance(data, (list, bytearray, memoryview)):
                data = bytes(data)
            if data is None and selected_file.path:
                data = Path(selected_file.path).read_bytes()
            if data is None:
                self.feedback("ไม่สามารถอ่านไฟล์ที่เลือกได้", error=True)
                return
            self.pending_import = preview_users(self.service, selected_file.name, data)
            self.close_dialog()
            self.import_preview_dialog()
        except (AppError, OSError, TypeError, UnicodeError, ValueError) as error:
            self.feedback(str(error), error=True)

    def import_users_dialog(self) -> None:
        async def download_example() -> None:
            try:
                await self.file_picker.save_file(
                    file_name="user-import-example.xlsx",
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["xlsx"],
                    src_bytes=template_bytes("xlsx"),
                )
            except (OSError, ValueError) as error:
                self.feedback(f"ดาวน์โหลดไฟล์ตัวอย่างไม่สำเร็จ: {error}", error=True)

        pick_action = ft.PickFiles(
            self.file_picker,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["csv", "xlsx"],
            with_data=True,
            cancel_upload_on_window_blur=False,
        )
        content = ft.Column(
            [
                ft.Text("เลือกไฟล์ CSV หรือ XLSX เพื่อดูก่อนนำเข้า", color=MUTED),
                ft.OutlinedButton(
                    "ดาวน์โหลดไฟล์ตัวอย่าง (.xlsx)",
                    icon=ft.Icons.DOWNLOAD_OUTLINED,
                    on_click=lambda _: self.page.run_task(download_example),
                ),
            ],
            spacing=14,
            tight=True,
        )
        self.dialog("Import ผู้ใช้", content, "เลือกไฟล์", action=pick_action)

    def import_preview_dialog(self) -> None:
        preview = self.pending_import
        if preview is None:
            return
        rows = [
            ft.Row(
                [
                    ft.Text(f"แถว {row.number}", width=70),
                    ft.Text(row.values["username"] or "-", width=130),
                    ft.Text(row.values["full_name"] or "-", expand=True),
                    ft.Text("พร้อมนำเข้า" if not row.errors else ", ".join(row.errors), color=SUCCESS if not row.errors else DANGER, expand=True),
                ]
            )
            for row in preview.rows
        ]

        def commit(_):
            created, errors = import_preview(self.service, self.user.id, preview)  # type: ignore[union-attr]
            self.close_dialog()
            self.pending_import = None
            self.feedback(f"นำเข้าแล้ว {created} คน" + (f"; ผิดพลาด {len(errors)} แถว" if errors else ""), error=bool(errors))
            self.render()

        self.dialog(
            "ตรวจสอบก่อนนำเข้า",
            ft.Column([ft.Text(f"พร้อม {preview.valid_count} แถว · ผิดพลาด {preview.error_count} แถว", weight=ft.FontWeight.BOLD), *rows], spacing=8),
            f"นำเข้า {preview.valid_count} คน",
            commit,
            width=780,
        )

    def equipment_view(self) -> ft.Control:
        tabs = ft.Row(
            [
                ft.Button("อุปกรณ์รายชิ้น", bgcolor="#eaf2ff" if self.equipment_tab == "units" else None, color=PRIMARY if self.equipment_tab == "units" else TEXT, on_click=lambda _: self.set_equipment_tab("units")),
                ft.Button("ชนิดอุปกรณ์", bgcolor="#eaf2ff" if self.equipment_tab == "types" else None, color=PRIMARY if self.equipment_tab == "types" else TEXT, on_click=lambda _: self.set_equipment_tab("types")),
            ]
        )
        if self.equipment_tab == "types":
            rows = self.service.list_equipment_types(self.query)
            action = ft.Button("เพิ่มชนิดอุปกรณ์", icon=ft.Icons.ADD, bgcolor=PRIMARY, color=ft.Colors.WHITE, on_click=lambda _: self.equipment_type_dialog())
            table_rows = [[
                ft.Text(row["name"], weight=ft.FontWeight.W_600),
                ft.Text(row["category_name"]),
                ft.Text(row["brand"] or "-"),
                ft.Text(row["model"] or "-"),
                ft.Text(f"{row['unit_count']} ชิ้น"),
                status_chip(row["status"]),
                ft.Row([row_action(ft.Icons.EDIT_OUTLINED, "แก้ไข", lambda _, item=row: self.equipment_type_dialog(item)), row_action(ft.Icons.BLOCK if row["status"] == "active" else ft.Icons.CHECK_CIRCLE_OUTLINE, "เปลี่ยนสถานะ", lambda _, item=row: self.equipment_type_status_dialog(item))], spacing=0),
            ] for row in rows]
            table = self.table(["ชนิดอุปกรณ์", "หมวดหมู่", "ยี่ห้อ", "รุ่น", "จำนวน", "สถานะ", "จัดการ"], table_rows, "ไม่พบชนิดอุปกรณ์")
        else:
            rows = self.service.list_units(self.query)
            action = ft.Button("เพิ่มอุปกรณ์", icon=ft.Icons.ADD, bgcolor=PRIMARY, color=ft.Colors.WHITE, on_click=lambda _: self.unit_dialog())
            table_rows = [[
                ft.Text(row["asset_code"], weight=ft.FontWeight.W_600, color=PRIMARY),
                ft.Text(row["type_name"]),
                ft.Text(row["category_name"]),
                ft.Text(" · ".join(value for value in [row["brand"], row["model"]] if value) or "-"),
                ft.Text(row["storage_location"]),
                status_chip(row["status"]),
                ft.Row([row_action(ft.Icons.EDIT_OUTLINED, "แก้ไข", lambda _, item=row: self.unit_dialog(item)), row_action(ft.Icons.BLOCK if row["status"] == "available" else ft.Icons.CHECK_CIRCLE_OUTLINE, "เปลี่ยนสถานะ", lambda _, item=row: self.unit_status_dialog(item), visible=row["status"] != "borrowed")], spacing=0),
            ] for row in rows]
            table = self.table(["Asset code", "ชนิดอุปกรณ์", "หมวดหมู่", "ยี่ห้อ / รุ่น", "ตำแหน่ง", "สถานะ", "จัดการ"], table_rows, "ไม่พบอุปกรณ์")
        return ft.Column(
            [title("อุปกรณ์", "แยกชนิดอุปกรณ์ออกจากทรัพย์สินแต่ละชิ้น", action), tabs, self.search_bar("ค้นหาชื่อ รุ่น asset code หรือตำแหน่ง", self.set_query), table],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def set_equipment_tab(self, tab: str) -> None:
        self.equipment_tab = tab
        self.query = ""
        self.render()

    def equipment_type_dialog(self, row=None) -> None:
        name = ft.TextField(label="ชื่อชนิดอุปกรณ์ *", value=row["name"] if row else "")
        category = dropdown("หมวดหมู่ *", self.service.list_master("category", active_only=True), value=row["category_id"] if row else None)
        brand = ft.TextField(label="ยี่ห้อ", value=(row["brand"] or "") if row else "")
        model = ft.TextField(label="รุ่น", value=(row["model"] or "") if row else "")
        description = ft.TextField(label="รายละเอียด", value=(row["description"] or "") if row else "", multiline=True, min_lines=2)

        def save(_):
            try:
                if not category.value:
                    raise AppError("กรุณาเลือกหมวดหมู่")
                self.service.save_equipment_type(
                    self.user.id,  # type: ignore[union-attr]
                    type_id=row["id"] if row else None,
                    name=name.value or "",
                    category_id=int(category.value),
                    brand=brand.value or "",
                    model=model.value or "",
                    description=description.value or "",
                )
                self.close_dialog()
                self.feedback("บันทึกชนิดอุปกรณ์แล้ว")
                self.render()
            except (AppError, ValueError) as error:
                self.feedback(str(error), error=True)

        self.dialog("แก้ไขชนิดอุปกรณ์" if row else "เพิ่มชนิดอุปกรณ์", ft.Column([name, category, ft.Row([brand, model]), description], spacing=12, tight=True), "บันทึก", save)

    def equipment_type_status_dialog(self, row) -> None:
        status = "inactive" if row["status"] == "active" else "active"

        def save(_):
            try:
                self.service.set_equipment_type_status(self.user.id, row["id"], status)  # type: ignore[union-attr]
                self.close_dialog()
                self.feedback("เปลี่ยนสถานะชนิดอุปกรณ์แล้ว")
                self.render()
            except AppError as error:
                self.close_dialog()
                self.feedback(str(error), error=True)

        self.confirm("ยืนยันเปลี่ยนสถานะ", f"ต้องการ{STATUS_LABELS[status]} {row['name']} ใช่หรือไม่", "ยืนยัน", save)

    def unit_dialog(self, row=None) -> None:
        equipment_type = dropdown("ชนิดอุปกรณ์ *", self.service.list_equipment_types(active_only=True), value=row["equipment_type_id"] if row else None)
        asset_code = ft.TextField(label="Asset code *", value=row["asset_code"] if row else "")
        location = ft.TextField(label="ตำแหน่งจัดเก็บ *", value=row["storage_location"] if row else "")

        def save(_):
            try:
                if not equipment_type.value:
                    raise AppError("กรุณาเลือกชนิดอุปกรณ์")
                self.service.save_unit(
                    self.user.id,  # type: ignore[union-attr]
                    unit_id=row["id"] if row else None,
                    equipment_type_id=int(equipment_type.value),
                    asset_code=asset_code.value or "",
                    storage_location=location.value or "",
                )
                self.close_dialog()
                self.feedback("บันทึกอุปกรณ์แล้ว")
                self.render()
            except (AppError, ValueError) as error:
                self.feedback(str(error), error=True)

        self.dialog("แก้ไขอุปกรณ์" if row else "เพิ่มอุปกรณ์", ft.Column([equipment_type, asset_code, location], spacing=12, tight=True), "บันทึก", save)

    def unit_status_dialog(self, row) -> None:
        status = "inactive" if row["status"] == "available" else "available"

        def save(_):
            try:
                self.service.set_unit_status(self.user.id, row["id"], status)  # type: ignore[union-attr]
                self.close_dialog()
                self.feedback("เปลี่ยนสถานะอุปกรณ์แล้ว")
                self.render()
            except AppError as error:
                self.close_dialog()
                self.feedback(str(error), error=True)

        self.confirm("ยืนยันเปลี่ยนสถานะ", f"ต้องการเปลี่ยน {row['asset_code']} เป็น “{STATUS_LABELS[status]}” ใช่หรือไม่", "ยืนยัน", save)

    def master_view(self) -> ft.Control:
        labels = {"faculty": "คณะ", "department": "สาขา/ภาควิชา", "cohort": "รุ่นนักศึกษา", "class_group": "หมู่เรียน", "category": "หมวดอุปกรณ์"}
        descriptions = {
            "faculty": "คณะที่ใช้ระบุสังกัดของนักศึกษา อาจารย์ และเจ้าหน้าที่",
            "department": "สาขาหรือภาควิชาภายใต้คณะ ใช้ระบุสังกัดของผู้ยืม",
            "cohort": "รุ่นของนักศึกษาภายใต้สาขา เช่น รุ่น 2568",
            "class_group": "หมู่เรียนภายใต้รุ่น ใช้เมื่อรุ่นเดียวกันมีหลายกลุ่ม",
            "category": "หมวดสำหรับจัดกลุ่มชนิดอุปกรณ์ เช่น คอมพิวเตอร์ หรือภาพและเสียง",
        }
        rows = self.service.list_master(self.master_kind)
        kind_tabs = ft.Row(
            [
                ft.Button(
                    label,
                    bgcolor="#eaf2ff" if key == self.master_kind else None,
                    color=PRIMARY if key == self.master_kind else TEXT,
                    height=44,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                    on_click=lambda _, target=key: self.set_master_kind(target),
                )
                for key, label in labels.items()
            ],
            wrap=True,
            spacing=8,
            run_spacing=8,
        )
        table_rows = [[
            ft.Text(row["name"], weight=ft.FontWeight.W_600),
            ft.Text(row["parent_name"] or "ไม่ต้องระบุ", color=MUTED),
            status_chip(row["status"]),
            ft.Row([row_action(ft.Icons.EDIT_OUTLINED, "แก้ไข", lambda _, item=row: self.master_dialog(item)), row_action(ft.Icons.BLOCK if row["status"] == "active" else ft.Icons.CHECK_CIRCLE_OUTLINE, "เปลี่ยนสถานะ", lambda _, item=row: self.master_status_dialog(item))], spacing=0),
        ] for row in rows]
        guide = ft.Container(
            ft.Row([ft.Icon(ft.Icons.INFO_OUTLINE, color=PRIMARY), ft.Text(descriptions[self.master_kind], color=MUTED, expand=True)]),
            padding=14,
            bgcolor="#eaf2ff",
            border_radius=12,
        )
        return ft.Column(
            [
                title("ข้อมูลอ้างอิงระบบ", "รายการตัวเลือกที่นำไปใช้ในข้อมูลผู้ใช้และอุปกรณ์", ft.Button(f"เพิ่ม{labels[self.master_kind]}", icon=ft.Icons.ADD, bgcolor=PRIMARY, color=ft.Colors.WHITE, on_click=lambda _: self.master_dialog())),
                kind_tabs,
                guide,
                self.table([labels[self.master_kind], "อยู่ภายใต้", "สถานะ", "จัดการ"], table_rows, f"ยังไม่มีข้อมูล{labels[self.master_kind]}"),
            ],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def set_master_kind(self, kind: str) -> None:
        self.master_kind = kind
        self.render()

    def master_dialog(self, row=None) -> None:
        labels = {"faculty": "คณะ", "department": "สาขา/ภาควิชา", "cohort": "รุ่นนักศึกษา", "class_group": "หมู่เรียน", "category": "หมวดอุปกรณ์"}
        parent_kinds = {"department": ("faculty", "คณะ"), "cohort": ("department", "สาขา/ภาควิชา"), "class_group": ("cohort", "รุ่นนักศึกษา")}
        name = ft.TextField(label=f"ชื่อ{labels[self.master_kind]} *", value=row["name"] if row else "")
        parent = None
        if self.master_kind in parent_kinds:
            parent_kind, parent_label = parent_kinds[self.master_kind]
            parent_column = {"department": "faculty_id", "cohort": "department_id", "class_group": "cohort_id"}[self.master_kind]
            parent = dropdown(parent_label, self.service.list_master(parent_kind, active_only=True), value=row[parent_column] if row else None)

        def save(_):
            try:
                self.service.save_master(self.user.id, self.master_kind, name.value or "", parent_id=int(parent.value) if parent and parent.value else None, record_id=row["id"] if row else None)  # type: ignore[union-attr]
                self.close_dialog()
                self.feedback("บันทึกข้อมูลหลักแล้ว")
                self.render()
            except (AppError, ValueError) as error:
                self.feedback(str(error), error=True)

        controls = [name] + ([parent] if parent else [])
        self.dialog(f"{'แก้ไข' if row else 'เพิ่ม'}{labels[self.master_kind]}", ft.Column(controls, spacing=12, tight=True), "บันทึก", save)

    def master_status_dialog(self, row) -> None:
        status = "inactive" if row["status"] == "active" else "active"

        def save(_):
            try:
                self.service.set_master_status(self.user.id, self.master_kind, row["id"], status)  # type: ignore[union-attr]
                self.close_dialog()
                self.feedback("เปลี่ยนสถานะข้อมูลหลักแล้ว")
                self.render()
            except AppError as error:
                self.close_dialog()
                self.feedback(str(error), error=True)

        self.confirm("ยืนยันเปลี่ยนสถานะ", f"ต้องการ{STATUS_LABELS[status]} “{row['name']}” ใช่หรือไม่", "ยืนยัน", save)

    def account_view(self) -> ft.Control:
        line_status = "เชื่อมแล้ว" if self.user.line_user_id else "ยังไม่เชื่อม"  # type: ignore[union-attr]
        line_action = (
            ft.OutlinedButton("ยกเลิกการเชื่อม LINE", icon=ft.Icons.LINK_OFF, on_click=lambda _: self.unlink_line_dialog())
            if self.user.line_user_id  # type: ignore[union-attr]
            else ft.Button("เชื่อม LINE", icon=ft.Icons.LINK, bgcolor=PRIMARY, color=ft.Colors.WHITE, on_click=lambda _: self.start_line_login())
        )
        profile = card(
            ft.Column(
                [
                    ft.Text(self.user.full_name, size=22, weight=ft.FontWeight.BOLD),  # type: ignore[union-attr]
                    ft.Text(f"@{self.user.username} · {ROLE_LABELS[self.user.role]} · {TYPE_LABELS[self.user.user_type]}", color=MUTED),  # type: ignore[union-attr]
                    ft.Divider(),
                    ft.Row([ft.Text("สถานะ LINE", expand=True), ft.Text(line_status, color=SUCCESS if self.user.line_user_id else MUTED), line_action]),  # type: ignore[union-attr]
                ],
                spacing=12,
            )
        )
        return ft.Column([title("บัญชี", "รหัสผ่านและการเชื่อม LINE"), profile, self.password_screen(forced=False)], spacing=16, expand=True, scroll=ft.ScrollMode.AUTO)

    def unlink_line_dialog(self) -> None:
        def unlink(_):
            self.service.unlink_line(self.user.id)  # type: ignore[union-attr]
            self.user = self.service.get_user(self.user.id)  # type: ignore[union-attr]
            self.close_dialog()
            self.feedback("ยกเลิกการเชื่อม LINE แล้ว")
            self.render()

        self.confirm("ยกเลิกการเชื่อม LINE", "คุณยังเข้าสู่ระบบด้วย username และรหัสผ่านได้ตามปกติ", "ยกเลิกการเชื่อม", unlink)
