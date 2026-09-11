from __future__ import annotations

from dataclasses import dataclass

import flet as ft

from app.components.common import (
    build_card_list,
    build_data_card,
    build_filter_bar,
    build_form_dialog,
    build_page_header,
    build_state_view,
    build_status_chip,
    build_table_surface,
    close_dialog,
    handle_mobile_resize,
    open_dialog,
    update_control,
)
from app.contracts import AppUser, AuthService, Permission, RecordStatus, Role, has_permission
from app.security import validate_password_strength
from app.services.fake_services import FakeInventoryService
from app.theme import CONTROL_RADIUS


@dataclass(frozen=True)
class PersonRow:
    kind: str
    profile_id: int | None
    code: str
    name: str
    email: str | None
    department: str | None
    status: str
    account: AppUser | None


class PeopleDirectoryView(ft.Container):
    """One simple directory for staff, borrowers, and login accounts.

    This is the everyday entry point: one search, one list, and one action menu
    per person. The older detailed view remains in the codebase for compatibility.
    """

    def __init__(
        self,
        service: FakeInventoryService | None = None,
        *,
        mobile: bool = False,
        current_user: AppUser | None = None,
        auth_service: AuthService | None = None,
    ) -> None:
        super().__init__(expand=True, padding=0)
        self.service = service or FakeInventoryService()
        self.mobile = mobile
        self.current_user = current_user
        self.auth_service = auth_service
        self._table_width: float | None = None
        self._surface_width: float | None = None
        self._editing_kind: str | None = None
        self._editing_profile_id: int | None = None
        self._account_user_id: int | None = None

        self.search = ft.TextField(
            label="ค้นหาคนในระบบ",
            hint_text="ชื่อ รหัส อีเมล หรือ LINE",
            prefix_icon=ft.Icons.SEARCH,
            width=float("inf"),
            height=52,
            border_radius=CONTROL_RADIUS,
            on_change=self._handle_search,
        )
        self.kind_filter = ft.Dropdown(
            label="ประเภท",
            value="all",
            options=[
                ft.dropdown.Option("all", "ทุกประเภท"),
                ft.dropdown.Option("staff", "เจ้าหน้าที่"),
                ft.dropdown.Option("borrower", "ผู้ยืม"),
                ft.dropdown.Option("account", "บัญชีที่ยังไม่ผูกบุคคล"),
            ],
            height=52,
            width=190,
            border_radius=CONTROL_RADIUS,
            on_select=self._handle_filter,
        )
        self.status_filter = ft.Dropdown(
            label="สถานะ",
            value="all",
            options=[
                ft.dropdown.Option("all", "ทุกสถานะ"),
                ft.dropdown.Option("active", "ใช้งาน"),
                ft.dropdown.Option("inactive", "ปิดใช้งาน"),
                ft.dropdown.Option("unlinked", "ยังไม่มีบัญชี"),
            ],
            height=52,
            width=170,
            border_radius=CONTROL_RADIUS,
            on_select=self._handle_filter,
        )

        self.feedback = ft.Text("", size=13, color=ft.Colors.GREY_700, weight=ft.FontWeight.W_500)
        self.summary = ft.Row(spacing=12, wrap=True)
        self.people_container = ft.Container(expand=True)

        self.profile_kind = ft.Dropdown(
            label="ประเภทบุคคล",
            value="borrower",
            options=[
                ft.dropdown.Option("borrower", "ผู้ยืม"),
                ft.dropdown.Option("staff", "เจ้าหน้าที่"),
            ],
            on_select=self._handle_profile_kind_change,
        )
        self.profile_code = ft.TextField(label="รหัส", hint_text="ระบบสร้างให้โดยอัตโนมัติ")
        self.profile_name = ft.TextField(label="ชื่อ-นามสกุล", autofocus=True)
        self.profile_department = ft.TextField(label="หน่วยงาน / ภาควิชา")
        self.profile_email = ft.TextField(label="อีเมล", hint_text="ใช้เชื่อมบัญชีเดิมได้")
        self.profile_status = ft.Dropdown(
            label="สถานะข้อมูลบุคคล",
            value=RecordStatus.ACTIVE.value,
            options=[
                ft.dropdown.Option(RecordStatus.ACTIVE.value, "ใช้งาน"),
                ft.dropdown.Option(RecordStatus.INACTIVE.value, "ปิดใช้งาน"),
            ],
        )
        self.profile_dialog = build_form_dialog(
            title="เพิ่มบุคคล",
            icon=ft.Icons.PERSON_ADD_ALT_1,
            content=ft.Column(
                controls=[
                    self.profile_kind,
                    self.profile_code,
                    self.profile_name,
                    self.profile_department,
                    self.profile_email,
                    self.profile_status,
                ],
                spacing=12,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            save_label="บันทึก",
            on_save=self._save_profile,
            on_cancel=lambda e: close_dialog(self, self.profile_dialog),
        )

        self.account_role = ft.Dropdown(
            label="สิทธิ์การใช้งาน",
            options=[
                ft.dropdown.Option(Role.USER.value, "ผู้ใช้ทั่วไป"),
                ft.dropdown.Option(Role.ADMIN.value, "ผู้ดูแลระบบ"),
            ],
        )
        self.account_status = ft.Dropdown(
            label="สถานะบัญชี",
            options=[
                ft.dropdown.Option(RecordStatus.ACTIVE.value, "ใช้งาน"),
                ft.dropdown.Option(RecordStatus.INACTIVE.value, "ปิดใช้งาน"),
            ],
        )
        self.account_staff = ft.Dropdown(label="ผูกเจ้าหน้าที่", options=[])
        self.account_borrower = ft.Dropdown(label="ผูกผู้ยืม", options=[])
        self.account_password = ft.TextField(
            label="ตั้งรหัสผ่านใหม่ (ถ้าต้องการ)",
            password=True,
            can_reveal_password=True,
            hint_text="อย่างน้อย 8 ตัวอักษร",
        )
        self.account_dialog = build_form_dialog(
            title="จัดการบัญชีเข้าใช้",
            icon=ft.Icons.MANAGE_ACCOUNTS_OUTLINED,
            content=ft.Column(
                controls=[
                    self.account_role,
                    self.account_status,
                    self.account_staff,
                    self.account_borrower,
                    self.account_password,
                ],
                spacing=12,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            save_label="บันทึกบัญชี",
            on_save=self._save_account,
            on_cancel=lambda e: close_dialog(self, self.account_dialog),
        )

        self._build_view()
        self.on_size_change = self._handle_resize

    def _build_view(self) -> None:
        header = build_page_header(
            title="คนในระบบ",
            subtitle="ค้นหา แก้ไข และเชื่อมบัญชีของทุกคนจากหน้าเดียว",
            icon=ft.Icons.PEOPLE,
        )
        toolbar = build_filter_bar(
            search_control=self.search,
            action_controls=[
                self.kind_filter,
                self.status_filter,
                ft.Button(
                    "เพิ่มบุคคล",
                    icon=ft.Icons.PERSON_ADD,
                    height=52,
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.BLUE_600,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=CONTROL_RADIUS)
                    ),
                    on_click=self._open_new_profile,
                ),
                ft.OutlinedButton(
                    "รีเฟรช",
                    icon=ft.Icons.REFRESH,
                    height=52,
                    on_click=self._handle_reset,
                ),
            ],
            search_col=4,
        )
        self.content = ft.Column(
            controls=[header, self.summary, toolbar, self.feedback, self.people_container],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        self._render()

    @staticmethod
    def _profile_id(value: object) -> int | None:
        try:
            return int(str(value))
        except (TypeError, ValueError):
            try:
                return int(str(value).rsplit("-", 1)[-1])
            except (TypeError, ValueError):
                return None

    def _rows(self) -> list[PersonRow]:
        users = self.auth_service.list_users() if self.auth_service is not None else []
        used_user_ids: set[int] = set()
        by_staff = {user.staff_id: user for user in users if user.staff_id is not None}
        by_borrower = {user.borrower_id: user for user in users if user.borrower_id is not None}

        rows: list[PersonRow] = []
        for staff in self.service.list_staff(include_inactive=True):
            staff_id = self._profile_id(staff.id)
            account = by_staff.get(staff_id)
            if account is not None:
                used_user_ids.add(account.id)
            if account is None and staff.email:
                account = next(
                    (user for user in users if user.id not in used_user_ids and user.email and user.email.casefold() == staff.email.casefold()),
                    None,
                )
            if account is not None:
                used_user_ids.add(account.id)
            effective_status = account.status.value if account is not None and account.status is RecordStatus.INACTIVE else staff.status
            rows.append(PersonRow("staff", staff_id, staff.staff_code, staff.full_name, staff.email, None, effective_status, account))

        for borrower in self.service.list_borrowers(include_inactive=True):
            borrower_id = self._profile_id(borrower.id)
            account = by_borrower.get(borrower_id)
            if account is not None:
                used_user_ids.add(account.id)
            if account is None and borrower.email:
                account = next(
                    (user for user in users if user.id not in used_user_ids and user.email and user.email.casefold() == borrower.email.casefold()),
                    None,
                )
            if account is not None:
                used_user_ids.add(account.id)
            effective_status = account.status.value if account is not None and account.status is RecordStatus.INACTIVE else borrower.status
            rows.append(PersonRow("borrower", borrower_id, borrower.borrower_code, borrower.full_name, borrower.email, borrower.department, effective_status, account))

        for user in users:
            if user.id in used_user_ids:
                continue
            rows.append(PersonRow("account", None, "", user.display_name, user.email, None, user.status.value, user))
        return rows

    def _filtered_rows(self) -> list[PersonRow]:
        keyword = (self.search.value or "").strip().casefold()
        kind = self.kind_filter.value or "all"
        status = self.status_filter.value or "all"
        rows = self._rows()
        if keyword:
            rows = [
                row
                for row in rows
                if keyword in row.name.casefold()
                or keyword in row.code.casefold()
                or keyword in (row.email or "").casefold()
                or (row.account is not None and row.account.line_sub is not None and keyword == "line")
            ]
        if kind != "all":
            rows = [row for row in rows if row.kind == kind]
        if status == "unlinked":
            rows = [row for row in rows if row.account is None]
        elif status != "all":
            rows = [row for row in rows if row.status == status or (row.account is not None and row.account.status.value == status)]
        return rows

    def _render_summary(self, rows: list[PersonRow]) -> None:
        all_rows = self._rows()
        cards = [
            ("ทั้งหมด", len(all_rows), ft.Icons.PEOPLE_OUTLINED),
            ("เจ้าหน้าที่", sum(row.kind == "staff" for row in all_rows), ft.Icons.BADGE_OUTLINED),
            ("ผู้ยืม", sum(row.kind == "borrower" for row in all_rows), ft.Icons.PERSON_OUTLINED),
            ("รอเชื่อมบัญชี", sum(row.account is None for row in all_rows), ft.Icons.LINK_OFF),
        ]
        self.summary.controls = [
            ft.Container(
                content=ft.Row(
                    controls=[ft.Icon(icon, color=ft.Colors.BLUE_700), ft.Column([ft.Text(label, size=12), ft.Text(str(value), size=20, weight=ft.FontWeight.BOLD)], spacing=0)],
                    spacing=10,
                ),
                padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                bgcolor=ft.Colors.BLUE_50,
                border_radius=CONTROL_RADIUS,
            )
            for label, value, icon in cards
        ]

    def _render(self) -> None:
        rows = self._filtered_rows()
        self._render_summary(rows)
        if not rows:
            self.people_container.content = build_state_view(
                "ไม่พบคนในระบบ",
                "ลองเปลี่ยนคำค้นหาหรือตัวกรอง หรือเพิ่มบุคคลใหม่",
                icon=ft.Icons.PEOPLE_OUTLINED,
            )
            return
        if self.mobile:
            self.people_container.content = build_card_list([self._person_card(row) for row in rows])
            return
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ชื่อ"), expand=3),
                ft.DataColumn(ft.Text("ประเภท"), expand=2),
                ft.DataColumn(ft.Text("รหัส"), expand=2),
                ft.DataColumn(ft.Text("การเข้าใช้"), expand=3),
                ft.DataColumn(ft.Text("สถานะ"), expand=2),
                ft.DataColumn(ft.Text("จัดการ"), expand=1),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(row.name, weight=ft.FontWeight.W_600)),
                        ft.DataCell(ft.Text(self._kind_label(row.kind))),
                        ft.DataCell(ft.Text(row.code or "—")),
                        ft.DataCell(ft.Text(self._login_label(row))),
                        ft.DataCell(build_status_chip(row.status, self._status_label(row))),
                        ft.DataCell(self._action_button(row)),
                    ]
                )
                for row in rows
            ],
            column_spacing=22,
            horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_200),
        )
        self.people_container.content = build_table_surface(
            table,
            table_width=1050,
            initial_width=self._surface_width or self._table_width,
            on_resized=self._record_surface_width,
        )

    @staticmethod
    def _kind_label(kind: str) -> str:
        return {"staff": "เจ้าหน้าที่", "borrower": "ผู้ยืม", "account": "บัญชีเข้าใช้"}.get(kind, kind)

    @staticmethod
    def _status_label(row: PersonRow) -> str:
        if row.account is None and row.kind != "account":
            return "ยังไม่มีบัญชี"
        return {"active": "ใช้งาน", "inactive": "ปิดใช้งาน"}.get(row.status, row.status)

    @staticmethod
    def _login_label(row: PersonRow) -> str:
        if row.account is None:
            return "ยังไม่มีบัญชี"
        methods = []
        if row.account.line_sub:
            methods.append("LINE")
        if row.account.email:
            methods.append("อีเมล")
        return " + ".join(methods) or "ไม่มีช่องทางเข้าใช้"

    def _person_card(self, row: PersonRow) -> ft.Container:
        actions = [self._action_button(row)]
        if row.account is None and row.kind != "account":
            actions.append(ft.Text("เพิ่มบัญชีได้เมื่อมีอีเมลหรือ LINE", size=12, color=ft.Colors.GREY_700))
        return build_data_card(
            title=row.name,
            icon=ft.Icons.BADGE_OUTLINED if row.kind == "staff" else ft.Icons.PERSON_OUTLINED,
            status=(row.status, self._status_label(row)),
            fields=[
                ("ประเภท", self._kind_label(row.kind)),
                ("รหัส", row.code or "—"),
                ("การเข้าใช้", self._login_label(row)),
                ("อีเมล", row.email or "ไม่มีอีเมล"),
            ],
            full_width_fields=["อีเมล"],
            header_actions=actions,
        )

    def _action_button(self, row: PersonRow) -> ft.Control:
        if row.kind == "account":
            return ft.Button("จัดการบัญชี", icon=ft.Icons.MANAGE_ACCOUNTS, on_click=lambda e, user=row.account: self._open_account(user))
        return ft.Button("แก้ไข", icon=ft.Icons.EDIT_OUTLINED, on_click=lambda e, item=row: self._open_profile(item))

    def _handle_search(self, e: ft.ControlEvent) -> None:
        self._render()

    def _handle_filter(self, e: ft.ControlEvent) -> None:
        self._render()

    def _handle_reset(self, e: ft.ControlEvent) -> None:
        self.search.value = ""
        self.kind_filter.value = "all"
        self.status_filter.value = "all"
        self._render()

    def _handle_resize(self, e: ft.LayoutSizeChangeEvent) -> None:
        self._table_width = e.width
        handle_mobile_resize(self, self._render, e)

    def _record_surface_width(self, width: float) -> None:
        self._surface_width = width

    def _set_feedback(self, message: str, *, error: bool = False) -> None:
        self.feedback.value = message
        self.feedback.color = ft.Colors.RED_700 if error else ft.Colors.GREEN_700
        update_control(self)

    def _can_manage(self) -> bool:
        if has_permission(self.current_user, Permission.MANAGE_PEOPLE):
            return True
        self._set_feedback("คุณไม่มีสิทธิ์จัดการคนในระบบ", error=True)
        return False

    def _next_code(self, kind: str) -> str:
        prefix = "ST" if kind == "staff" else "BR"
        records = self.service.list_staff(include_inactive=True) if kind == "staff" else self.service.list_borrowers(include_inactive=True)
        numbers = []
        for record in records:
            value = record.staff_code if kind == "staff" else record.borrower_code
            try:
                numbers.append(int(value.rsplit("-", 1)[-1]))
            except ValueError:
                continue
        return f"{prefix}-{max(numbers, default=0) + 1:03d}"

    def _open_new_profile(self, e: ft.ControlEvent | None) -> None:
        if not self._can_manage():
            return
        self._editing_kind = None
        self._editing_profile_id = None
        self.profile_dialog.title.controls[-1].value = "เพิ่มบุคคล"
        self.profile_kind.visible = True
        self.profile_kind.value = "borrower"
        self.profile_code.read_only = False
        self.profile_code.value = self._next_code("borrower")
        self.profile_name.value = ""
        self.profile_department.value = ""
        self.profile_email.value = ""
        self.profile_status.value = RecordStatus.ACTIVE.value
        self._handle_profile_kind_change(None)
        open_dialog(self, self.profile_dialog)

    def _open_profile(self, row: PersonRow) -> None:
        if not self._can_manage():
            return
        self._editing_kind = row.kind
        self._editing_profile_id = row.profile_id
        self.profile_dialog.title.controls[-1].value = f"แก้ไข{self._kind_label(row.kind)}"
        self.profile_kind.visible = False
        self.profile_code.read_only = True
        self.profile_code.value = row.code
        self.profile_name.value = row.name
        self.profile_department.value = row.department or ""
        self.profile_email.value = row.email or ""
        self.profile_status.value = row.status
        self._handle_profile_kind_change(None)
        open_dialog(self, self.profile_dialog)

    def _handle_profile_kind_change(self, e: ft.ControlEvent | None) -> None:
        self.profile_department.visible = self.profile_kind.value == "borrower" or self._editing_kind == "borrower"
        if self._editing_kind is None:
            self.profile_code.value = self._next_code(self.profile_kind.value or "borrower")
        update_control(self.profile_dialog)

    def _save_profile(self, e: ft.ControlEvent) -> None:
        if not self._can_manage():
            return
        kind = self._editing_kind or self.profile_kind.value or "borrower"
        code = (self.profile_code.value or "").strip()
        name = (self.profile_name.value or "").strip()
        department = (self.profile_department.value or "").strip() or None
        email = (self.profile_email.value or "").strip() or None
        status = self.profile_status.value or RecordStatus.ACTIVE.value
        if not code or not name:
            self._set_feedback("กรุณาใส่รหัสและชื่อ", error=True)
            return
        if kind == "staff":
            existing = self.service.get_staff(code)
            saved = self.service.update_staff(code, full_name=name, email=email, status=status) if existing else self.service.create_staff(code, name, email=email, status=status)
        else:
            existing = self.service.get_borrower(code)
            saved = self.service.update_borrower(code, full_name=name, department=department, email=email, status=status) if existing else self.service.create_borrower(code, name, department=department, email=email, status=status)
        if saved is None:
            self._set_feedback("บันทึกไม่สำเร็จ กรุณาตรวจสอบรหัสหรือข้อมูลซ้ำ", error=True)
            return
        self._auto_link_by_email(kind, self._profile_id(saved.id), email)
        self._set_feedback(f"บันทึก {name} เรียบร้อย")
        close_dialog(self, self.profile_dialog)
        self._render()

    def _auto_link_by_email(self, kind: str, profile_id: int | None, email: str | None) -> None:
        if self.auth_service is None or profile_id is None or not email:
            return
        user = next((candidate for candidate in self.auth_service.list_users() if candidate.email and candidate.email.casefold() == email.casefold()), None)
        if user is None or user.staff_id is not None or user.borrower_id is not None:
            return
        try:
            if kind == "staff":
                self.auth_service.set_user_staff(user.id, profile_id, actor=self.current_user)
            elif kind == "borrower":
                self.auth_service.set_user_borrower(user.id, profile_id, actor=self.current_user)
        except Exception:
            return

    def _open_account(self, user: AppUser | None) -> None:
        if user is None or not self._can_manage() or self.auth_service is None:
            return
        self._account_user_id = user.id
        self.account_role.value = user.role.value
        self.account_status.value = user.status.value
        self.account_password.value = ""
        self.account_staff.options = [ft.dropdown.Option("", "ไม่ผูกเจ้าหน้าที่")] + [ft.dropdown.Option(str(self._profile_id(item.id)), f"{item.staff_code} — {item.full_name}") for item in self.service.list_staff(include_inactive=True)]
        self.account_borrower.options = [ft.dropdown.Option("", "ไม่ผูกผู้ยืม")] + [ft.dropdown.Option(str(self._profile_id(item.id)), f"{item.borrower_code} — {item.full_name}") for item in self.service.list_borrowers(include_inactive=True)]
        self.account_staff.value = str(user.staff_id) if user.staff_id is not None else ""
        self.account_borrower.value = str(user.borrower_id) if user.borrower_id is not None else ""
        self.account_dialog.title.controls[-1].value = f"จัดการบัญชี: {user.display_name}"
        open_dialog(self, self.account_dialog)

    def _save_account(self, e: ft.ControlEvent) -> None:
        if not self._can_manage() or self.auth_service is None or self._account_user_id is None:
            return
        user_id = self._account_user_id
        status = RecordStatus(self.account_status.value)
        if self.current_user is not None and user_id == self.current_user.id and status is RecordStatus.INACTIVE:
            self._set_feedback("ไม่สามารถปิดใช้งานบัญชีของตัวเองได้", error=True)
            return
        password = (self.account_password.value or "").strip()
        if password:
            error = validate_password_strength(password)
            if error is not None:
                self._set_feedback(error, error=True)
                return
        try:
            updated = self.auth_service.set_user_role(user_id, Role(self.account_role.value), actor=self.current_user)
            self.auth_service.set_user_status(user_id, status, actor=self.current_user)
            staff_id = self._profile_id(self.account_staff.value) if self.account_staff.value else None
            borrower_id = self._profile_id(self.account_borrower.value) if self.account_borrower.value else None
            self.auth_service.set_user_staff(user_id, staff_id, actor=self.current_user)
            self.auth_service.set_user_borrower(user_id, borrower_id, actor=self.current_user)
            if password:
                self.auth_service.admin_reset_password(user_id, password, actor=self.current_user)
        except Exception as error:
            self._set_feedback(str(error) or "บันทึกบัญชีไม่สำเร็จ", error=True)
            return
        self._set_feedback(f"อัปเดตบัญชี {updated.display_name} เรียบร้อย")
        close_dialog(self, self.account_dialog)
        self._render()
