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
from app.services.fake_services import FakeInventoryService
from app.theme import CONTROL_RADIUS


class StaffBorrowersView(ft.Container):
    def __init__(
        self,
        service: FakeInventoryService | None = None,
        *,
        mobile: bool = False,
    ) -> None:
        super().__init__(expand=True, padding=0)
        self.service = service or FakeInventoryService()
        self.mobile = mobile
        self._table_width: float | None = None
        self._surface_width: float | None = None
        self.selected_mode = "staff"

        self.staff_search = ft.TextField(
            label="ค้นหาผู้บันทึกรายการ",
            hint_text="รหัส ST-001 หรือชื่อ",
            prefix_icon=ft.Icons.SEARCH,
            width=float("inf"),
            height=52,
            border_radius=CONTROL_RADIUS,
            on_change=self._handle_staff_search,
        )
        self.borrower_search = ft.TextField(
            label="ค้นหาผู้ยืม",
            hint_text="รหัส BR-001 หรือชื่อผู้ยืม",
            prefix_icon=ft.Icons.SEARCH,
            width=float("inf"),
            height=52,
            border_radius=CONTROL_RADIUS,
            on_change=self._handle_borrower_search,
        )

        self.staff_name = ft.TextField(label="ชื่อผู้บันทึกรายการ", hint_text="เช่น สมชาย ใจดี", expand=True)
        self.staff_code = ft.TextField(label="รหัสผู้บันทึก", hint_text="เช่น ST-003", expand=True)
        self.staff_email = ft.TextField(label="อีเมล", hint_text="ada@example.com", expand=True)

        self.borrower_name = ft.TextField(label="ชื่อเต็มผู้ยืม", hint_text="เช่น สมชาย ใจดี", expand=True)
        self.borrower_code = ft.TextField(label="รหัสผู้ยืม", hint_text="เช่น BR-003", expand=True)
        self.borrower_department = ft.TextField(label="หน่วยงาน / ภาควิชา", hint_text="เช่น ฝ่ายไอที หรืองานวิจัย", expand=True)
        self.borrower_email = ft.TextField(label="อีเมล", hint_text="somchai@example.com", expand=True)

        self.feedback = ft.Text("", size=13, color=ft.Colors.GREY_700, weight=ft.FontWeight.W_500)
        self.staff_container = ft.Container(expand=True)
        self.borrower_container = ft.Container(expand=True)
        self.mode_container = ft.Container(expand=True)

        self.btn_staff_tab = ft.Button(
            "ผู้บันทึกรายการ",
            icon=ft.Icons.BADGE,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
            ),
            on_click=self._switch_to_staff,
        )
        self.btn_borrower_tab = ft.OutlinedButton(
            "ผู้ยืม",
            icon=ft.Icons.PERSON_SEARCH,
            on_click=self._switch_to_borrowers,
        )
        self.staff_dialog = build_form_dialog(
            title="เพิ่มหรือแก้ไขผู้บันทึกรายการ",
            icon=ft.Icons.BADGE_OUTLINED,
            content=ft.Column(
                controls=[self.staff_code, self.staff_name, self.staff_email],
                spacing=12,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            save_label="บันทึกผู้บันทึก",
            on_save=self._handle_save_staff,
            on_cancel=lambda e: close_dialog(self, self.staff_dialog),
        )
        self.borrower_dialog = build_form_dialog(
            title="เพิ่มหรือแก้ไขผู้ยืม",
            icon=ft.Icons.PERSON_ADD_ALT_1,
            content=ft.Column(
                controls=[
                    self.borrower_code,
                    self.borrower_name,
                    self.borrower_department,
                    self.borrower_email,
                ],
                spacing=12,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            save_label="บันทึกผู้ยืม",
            on_save=self._handle_save_borrower,
            on_cancel=lambda e: close_dialog(self, self.borrower_dialog),
        )

        self._build_view()
        self.on_size_change = self._handle_resize

    def _build_view(self) -> None:
        header = build_page_header(
            title="คนในระบบ",
            subtitle="เก็บข้อมูลผู้บันทึกรายการและผู้ยืม",
            icon=ft.Icons.PEOPLE,
        )

        tab_switcher = ft.Row(
            controls=[
                self.btn_staff_tab,
                self.btn_borrower_tab,
            ],
            spacing=12,
        )

        self.content = ft.Column(
            controls=[
                header,
                tab_switcher,
                self.mode_container,
            ],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        self._refresh_mode_content()
        self._render_staff()
        self._render_borrowers()

    def _build_staff_tab(self) -> ft.Control:
        search_card = build_filter_bar(
            search_control=self.staff_search,
            action_controls=[
                ft.Button(
                    "เพิ่มผู้บันทึกรายการ",
                    icon=ft.Icons.PERSON_ADD,
                    height=52,
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.BLUE_600,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=CONTROL_RADIUS),
                    ),
                    on_click=self._open_new_staff,
                ),
                ft.OutlinedButton(
                    "รีเฟรช",
                    icon=ft.Icons.REFRESH,
                    height=52,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=CONTROL_RADIUS),
                    ),
                    on_click=self._handle_staff_reset,
                ),
            ],
        )

        return ft.Column(
            controls=[
                search_card,
                self.feedback,
                self.staff_container,
            ],
            spacing=16,
        )

    def _build_borrower_tab(self) -> ft.Control:
        search_card = build_filter_bar(
            search_control=self.borrower_search,
            action_controls=[
                ft.Button(
                    "เพิ่มผู้ยืม",
                    icon=ft.Icons.PERSON_ADD_ALT_1,
                    height=52,
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.BLUE_600,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=CONTROL_RADIUS),
                    ),
                    on_click=self._open_new_borrower,
                ),
                ft.OutlinedButton(
                    "รีเฟรช",
                    icon=ft.Icons.REFRESH,
                    height=52,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=CONTROL_RADIUS),
                    ),
                    on_click=self._handle_borrower_reset,
                ),
            ],
        )

        return ft.Column(
            controls=[
                search_card,
                self.feedback,
                self.borrower_container,
            ],
            spacing=16,
        )

    def _refresh_mode_content(self) -> None:
        if self.selected_mode == "staff":
            self.btn_staff_tab.style = ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE_600)
            self.btn_borrower_tab.style = None
            self.mode_container.content = self._build_staff_tab()
        else:
            self.btn_borrower_tab.style = ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE_600)
            self.btn_staff_tab.style = None
            self.mode_container.content = self._build_borrower_tab()

    def _translate_status(self, status: str) -> str:
        return {
            "active": "ใช้งาน",
            "inactive": "ไม่ใช้งาน",
        }.get(status, status.title())

    def _switch_to_staff(self, e: ft.ControlEvent) -> None:
        self.selected_mode = "staff"
        self._refresh_mode_content()
        update_control(self)

    def _switch_to_borrowers(self, e: ft.ControlEvent) -> None:
        self.selected_mode = "borrowers"
        self._refresh_mode_content()
        update_control(self)

    def _open_new_staff(self, e: ft.ControlEvent | None) -> None:
        self.staff_code.value = ""
        self.staff_name.value = ""
        self.staff_email.value = ""
        open_dialog(self, self.staff_dialog)

    def _open_new_borrower(self, e: ft.ControlEvent | None) -> None:
        self.borrower_code.value = ""
        self.borrower_name.value = ""
        self.borrower_department.value = ""
        self.borrower_email.value = ""
        open_dialog(self, self.borrower_dialog)

    def _render_staff(self) -> None:
        keyword = (self.staff_search.value or "").strip().lower()
        staff = self.service.list_staff(include_inactive=True)
        if keyword:
            staff = [item for item in staff if keyword in item.full_name.lower() or keyword in item.staff_code.lower()]

        if not staff:
            self.staff_container.content = build_state_view("ยังไม่มีผู้บันทึกรายการ", "เพิ่มชื่อของคุณก่อนทำรายการยืม", icon=ft.Icons.PEOPLE_OUTLINED)
            return

        if self.mobile:
            self.staff_container.content = build_card_list(
                [
                    build_data_card(
                        title=item.full_name,
                        icon=ft.Icons.BADGE_OUTLINED,
                        status=(item.status, self._translate_status(item.status)),
                        fields=[
                            ("รหัส", item.staff_code),
                            ("อีเมล", item.email or "ไม่มีอีเมล"),
                        ],
                        full_width_fields=["อีเมล"],
                        header_actions=[
                            ft.IconButton(
                                icon=ft.Icons.EDIT_OUTLINED,
                                tooltip="แก้ไขผู้บันทึกรายการ",
                                on_click=lambda e, code=item.staff_code, name=item.full_name, email=item.email: self._select_staff(code, name, email),
                            )
                        ],
                    )
                    for item in staff
                ]
            )
            return

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("รหัสผู้บันทึก"), expand=2),
                ft.DataColumn(ft.Text("ชื่อ"), expand=3),
                ft.DataColumn(ft.Text("อีเมล"), expand=3),
                ft.DataColumn(ft.Text("สถานะ"), expand=2),
                ft.DataColumn(ft.Text("จัดการ"), expand=1),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(item.staff_code, weight=ft.FontWeight.W_600)),
                        ft.DataCell(ft.Text(item.full_name)),
                        ft.DataCell(ft.Text(item.email or "ไม่มีอีเมล")),
                        ft.DataCell(build_status_chip(item.status, self._translate_status(item.status))),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.Icons.EDIT_OUTLINED,
                                tooltip="แก้ไขผู้บันทึกรายการ",
                                on_click=lambda e, code=item.staff_code, name=item.full_name, email=item.email: self._select_staff(code, name, email),
                            )
                        ),
                    ]
                )
                for item in staff
            ],
            column_spacing=28,
            horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_200),
        )
        self.staff_container.content = build_table_surface(
            table,
            initial_width=(
                self._surface_width
                if self._surface_width is not None
                else self._table_width
            ),
            on_resized=self._record_surface_width,
        )

    def _select_staff(self, code: str, name: str, email: str | None) -> None:
        self.staff_code.value = code
        self.staff_name.value = name
        self.staff_email.value = email or ""
        self.feedback.value = f"เลือกผู้บันทึก {code} แล้ว"
        self.feedback.color = ft.Colors.BLUE_700
        open_dialog(self, self.staff_dialog)

    def _render_borrowers(self) -> None:
        keyword = (self.borrower_search.value or "").strip().lower()
        borrowers = self.service.list_borrowers(include_inactive=True)
        if keyword:
            borrowers = [item for item in borrowers if keyword in item.full_name.lower() or keyword in item.borrower_code.lower()]

        if not borrowers:
            self.borrower_container.content = build_state_view("ไม่มีผู้ยืม", "ไม่มีข้อมูลผู้ยืมที่ตรงกับการค้นหานี้", icon=ft.Icons.PERSON_OUTLINED)
            return

        if self.mobile:
            self.borrower_container.content = build_card_list(
                [
                    build_data_card(
                        title=item.full_name,
                        icon=ft.Icons.PERSON_OUTLINED,
                        status=(item.status, self._translate_status(item.status)),
                        fields=[
                            ("รหัส", item.borrower_code),
                            ("หน่วยงาน", item.department or "ไม่มีหน่วยงาน"),
                            ("อีเมล", item.email or "ไม่มีอีเมล"),
                        ],
                        full_width_fields=["อีเมล"],
                        header_actions=[
                            ft.IconButton(
                                icon=ft.Icons.EDIT_OUTLINED,
                                tooltip="แก้ไขผู้ยืม",
                                on_click=lambda e, code=item.borrower_code, name=item.full_name, dept=item.department, email=item.email: self._select_borrower(code, name, dept, email),
                            )
                        ],
                    )
                    for item in borrowers
                ]
            )
            return

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("รหัสผู้ยืม"), expand=2),
                ft.DataColumn(ft.Text("ชื่อ"), expand=3),
                ft.DataColumn(ft.Text("หน่วยงาน"), expand=3),
                ft.DataColumn(ft.Text("อีเมล"), expand=3),
                ft.DataColumn(ft.Text("สถานะ"), expand=2),
                ft.DataColumn(ft.Text("จัดการ"), expand=1),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(item.borrower_code, weight=ft.FontWeight.W_600)),
                        ft.DataCell(ft.Text(item.full_name)),
                        ft.DataCell(ft.Text(item.department or "ไม่มีหน่วยงาน")),
                        ft.DataCell(ft.Text(item.email or "ไม่มีอีเมล")),
                        ft.DataCell(build_status_chip(item.status, self._translate_status(item.status))),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.Icons.EDIT_OUTLINED,
                                tooltip="แก้ไขผู้ยืม",
                                on_click=lambda e, code=item.borrower_code, name=item.full_name, dept=item.department, email=item.email: self._select_borrower(code, name, dept, email),
                            )
                        ),
                    ]
                )
                for item in borrowers
            ],
            column_spacing=24,
            horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_200),
        )
        self.borrower_container.content = build_table_surface(
            table,
            table_width=1150,
            initial_width=(
                self._surface_width
                if self._surface_width is not None
                else self._table_width
            ),
            on_resized=self._record_surface_width,
        )

    def _record_surface_width(self, width: float) -> None:
        self._surface_width = width

    def _select_borrower(self, code: str, name: str, dept: str | None, email: str | None) -> None:
        self.borrower_code.value = code
        self.borrower_name.value = name
        self.borrower_department.value = dept or ""
        self.borrower_email.value = email or ""
        self.feedback.value = f"เลือกผู้ยืม {code} แล้ว"
        self.feedback.color = ft.Colors.BLUE_700
        open_dialog(self, self.borrower_dialog)

    def _handle_staff_search(self, e: ft.ControlEvent) -> None:
        self._render_staff()

    def _handle_staff_reset(self, e: ft.ControlEvent) -> None:
        self.staff_search.value = ""
        self._render_staff()

    def _handle_resize(self, e: ft.LayoutSizeChangeEvent) -> None:
        self._table_width = e.width
        handle_mobile_resize(self, self._rerender_lists, e)

    def _rerender_lists(self) -> None:
        self._render_staff()
        self._render_borrowers()

    def _handle_borrower_search(self, e: ft.ControlEvent) -> None:
        self._render_borrowers()

    def _handle_borrower_reset(self, e: ft.ControlEvent) -> None:
        self.borrower_search.value = ""
        self._render_borrowers()

    def _handle_save_staff(self, e: ft.ControlEvent) -> None:
        code = (self.staff_code.value or "").strip()
        name = (self.staff_name.value or "").strip()
        email = (self.staff_email.value or "").strip() or None
        if not code or not name:
            self.feedback.value = "กรุณาใส่รหัสและชื่อผู้บันทึก"
            self.feedback.color = ft.Colors.RED_700
            update_control(self)
            return
        existing = self.service.get_staff(code)
        if existing is None:
            saved = self.service.create_staff(code, name, email=email)
        else:
            saved = self.service.update_staff(code, full_name=name, email=email)
        if saved is None:
            self.feedback.value = "บันทึกผู้บันทึกไม่สำเร็จ กรุณาตรวจสอบรหัสหรือข้อมูลซ้ำ"
            self.feedback.color = ft.Colors.RED_700
            update_control(self)
            return
        self.feedback.value = f"บันทึกผู้บันทึก {code} แล้ว"
        self.feedback.color = ft.Colors.GREEN_700
        self.staff_code.value = ""
        self.staff_name.value = ""
        self.staff_email.value = ""
        self._render_staff()
        close_dialog(self, self.staff_dialog)
        update_control(self)

    def _handle_save_borrower(self, e: ft.ControlEvent) -> None:
        code = (self.borrower_code.value or "").strip()
        name = (self.borrower_name.value or "").strip()
        department = (self.borrower_department.value or "").strip() or None
        email = (self.borrower_email.value or "").strip() or None
        if not code or not name:
            self.feedback.value = "กรุณาใส่รหัสผู้ยืมและชื่อ"
            self.feedback.color = ft.Colors.RED_700
            update_control(self)
            return
        existing = self.service.get_borrower(code)
        if existing is None:
            saved = self.service.create_borrower(code, name, department=department, email=email)
        else:
            saved = self.service.update_borrower(code, full_name=name, department=department, email=email)
        if saved is None:
            self.feedback.value = "บันทึกผู้ยืมไม่สำเร็จ กรุณาตรวจสอบรหัสหรือข้อมูลซ้ำ"
            self.feedback.color = ft.Colors.RED_700
            update_control(self)
            return
        self.feedback.value = f"บันทึกผู้ยืม {code} แล้ว"
        self.feedback.color = ft.Colors.GREEN_700
        self.borrower_code.value = ""
        self.borrower_name.value = ""
        self.borrower_department.value = ""
        self.borrower_email.value = ""
        self._render_borrowers()
        close_dialog(self, self.borrower_dialog)
        update_control(self)
