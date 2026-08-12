import flet as ft

from app.components.common import (
    build_card,
    build_page_header,
    build_state_view,
    build_status_chip,
    update_control,
)
from app.services.fake_services import FakeInventoryService
from app.theme import COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY


class StaffBorrowersView(ft.Container):
    def __init__(self, service: FakeInventoryService | None = None) -> None:
        super().__init__(expand=True, padding=0)
        self.service = service or FakeInventoryService()
        self.selected_mode = "staff"

        self.staff_search = ft.TextField(
            label="ค้นหาเจ้าหน้าที่",
            hint_text="รหัส ST-001 หรือชื่อเจ้าหน้าที่",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
        )
        self.borrower_search = ft.TextField(
            label="ค้นหาผู้ยืม",
            hint_text="รหัส BR-001 หรือชื่อผู้ยืม",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
        )

        self.staff_name = ft.TextField(label="ชื่อเต็มเจ้าหน้าที่", hint_text="เช่น Ada Lovelace", expand=True)
        self.staff_code = ft.TextField(label="รหัสเจ้าหน้าที่", hint_text="เช่น ST-003", expand=True)
        self.staff_email = ft.TextField(label="อีเมล", hint_text="ada@example.com", expand=True)

        self.borrower_name = ft.TextField(label="ชื่อเต็มผู้ยืม", hint_text="เช่น Lin Chen", expand=True)
        self.borrower_code = ft.TextField(label="รหัสผู้ยืม", hint_text="เช่น BR-003", expand=True)
        self.borrower_department = ft.TextField(label="หน่วยงาน / ภาควิชา", hint_text="เช่น Biochemistry", expand=True)
        self.borrower_email = ft.TextField(label="อีเมล", hint_text="lin@example.com", expand=True)

        self.feedback = ft.Text("", size=13, color=ft.Colors.GREY_700, weight=ft.FontWeight.W_500)
        self.staff_container = ft.Container(expand=True)
        self.borrower_container = ft.Container(expand=True)
        self.mode_container = ft.Container(expand=True)

        self.btn_staff_tab = ft.ElevatedButton(
            "เจ้าหน้าที่ (Staff)",
            icon=ft.Icons.BADGE,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
            ),
            on_click=self._switch_to_staff,
        )
        self.btn_borrower_tab = ft.OutlinedButton(
            "ผู้ยืม (Borrowers)",
            icon=ft.Icons.PERSON_SEARCH,
            on_click=self._switch_to_borrowers,
        )

        self._build_view()

    def _build_view(self) -> None:
        header = build_page_header(
            title="จัดการเจ้าหน้าที่ & ผู้ยืม",
            subtitle="ตรวจสอบ ค้นหา และบันทึกข้อมูลบุคลากรในระบบ",
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
        search_card = build_card(
            content=ft.Column(
                controls=[
                    ft.Row(controls=[self.staff_search], spacing=12),
                    ft.Row(
                        controls=[
                            ft.ElevatedButton(
                                "ค้นหา",
                                icon=ft.Icons.SEARCH,
                                style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE_600),
                                on_click=self._handle_staff_search,
                            ),
                            ft.OutlinedButton(
                                "รีเซ็ต",
                                icon=ft.Icons.REFRESH,
                                on_click=self._handle_staff_reset,
                            ),
                        ],
                        spacing=12,
                    ),
                ],
                spacing=12,
            ),
        )

        form_card = build_card(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.PERSON_ADD, size=18, color=ft.Colors.BLUE_600),
                            ft.Text("เพิ่ม / แก้ไขข้อมูลเจ้าหน้าที่", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        controls=[
                            self.staff_code,
                            self.staff_name,
                            self.staff_email,
                        ],
                        spacing=12,
                    ),
                    ft.ElevatedButton(
                        "บันทึกเจ้าหน้าที่",
                        icon=ft.Icons.SAVE,
                        style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.GREEN_600),
                        on_click=self._handle_save_staff,
                    ),
                ],
                spacing=12,
            ),
        )

        return ft.Column(
            controls=[
                search_card,
                form_card,
                self.feedback,
                self.staff_container,
            ],
            spacing=16,
        )

    def _build_borrower_tab(self) -> ft.Control:
        search_card = build_card(
            content=ft.Column(
                controls=[
                    ft.Row(controls=[self.borrower_search], spacing=12),
                    ft.Row(
                        controls=[
                            ft.ElevatedButton(
                                "ค้นหา",
                                icon=ft.Icons.SEARCH,
                                style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE_600),
                                on_click=self._handle_borrower_search,
                            ),
                            ft.OutlinedButton(
                                "รีเซ็ต",
                                icon=ft.Icons.REFRESH,
                                on_click=self._handle_borrower_reset,
                            ),
                        ],
                        spacing=12,
                    ),
                ],
                spacing=12,
            ),
        )

        form_card = build_card(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.PERSON_ADD_ALT_1, size=18, color=ft.Colors.BLUE_600),
                            ft.Text("เพิ่ม / แก้ไขข้อมูลผู้ยืม", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        controls=[
                            self.borrower_code,
                            self.borrower_name,
                        ],
                        spacing=12,
                    ),
                    ft.Row(
                        controls=[
                            self.borrower_department,
                            self.borrower_email,
                        ],
                        spacing=12,
                    ),
                    ft.ElevatedButton(
                        "บันทึกผู้ยืม",
                        icon=ft.Icons.SAVE,
                        style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.GREEN_600),
                        on_click=self._handle_save_borrower,
                    ),
                ],
                spacing=12,
            ),
        )

        return ft.Column(
            controls=[
                search_card,
                form_card,
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

    def _render_staff(self) -> None:
        keyword = (self.staff_search.value or "").strip().lower()
        staff = self.service.list_staff(include_inactive=True)
        if keyword:
            staff = [item for item in staff if keyword in item.full_name.lower() or keyword in item.staff_code.lower()]

        if not staff:
            self.staff_container.content = build_state_view("ไม่มีเจ้าหน้าที่", "ไม่มีข้อมูลเจ้าหน้าที่ที่ตรงกับการค้นหานี้", icon=ft.Icons.PEOPLE_OUTLINED)
            return

        cards = []
        for item in staff:
            avatar = ft.CircleAvatar(
                content=ft.Icon(ft.Icons.BADGE, size=18, color=ft.Colors.BLUE_700),
                bgcolor=ft.Colors.BLUE_50,
                radius=18,
            )
            card_content = ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            avatar,
                            ft.Column(
                                controls=[
                                    ft.Text(item.full_name, weight=ft.FontWeight.BOLD, size=14, color=COLOR_TEXT_PRIMARY),
                                    ft.Text(item.staff_code, size=12, color=COLOR_TEXT_SECONDARY),
                                ],
                                spacing=1,
                                tight=True,
                                expand=True,
                            ),
                        ],
                        spacing=10,
                    ),
                    ft.Divider(height=8, color=ft.Colors.GREY_200),
                    ft.Row(
                        controls=[
                            build_status_chip(item.status, self._translate_status(item.status)),
                        ],
                    ),
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.EMAIL_OUTLINED, size=14, color=COLOR_TEXT_SECONDARY),
                            ft.Text(item.email or "ไม่มีอีเมล", size=12, color=COLOR_TEXT_SECONDARY, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                        ],
                        spacing=4,
                    ),
                ],
                spacing=6,
                tight=True,
            )
            card = build_card(
                content=card_content,
                padding=12,
                width=240,
                on_click=lambda e, code=item.staff_code, name=item.full_name, email=item.email: self._select_staff(code, name, email),
            )
            cards.append(card)

        self.staff_container.content = ft.Row(controls=cards, wrap=True, spacing=12, run_spacing=12)

    def _select_staff(self, code: str, name: str, email: str | None) -> None:
        self.staff_code.value = code
        self.staff_name.value = name
        self.staff_email.value = email or ""
        self.feedback.value = f"เลือกเจ้าหน้าที่ {code} แล้ว"
        self.feedback.color = ft.Colors.BLUE_700
        update_control(self)

    def _render_borrowers(self) -> None:
        keyword = (self.borrower_search.value or "").strip().lower()
        borrowers = self.service.list_borrowers(include_inactive=True)
        if keyword:
            borrowers = [item for item in borrowers if keyword in item.full_name.lower() or keyword in item.borrower_code.lower()]

        if not borrowers:
            self.borrower_container.content = build_state_view("ไม่มีผู้ยืม", "ไม่มีข้อมูลผู้ยืมที่ตรงกับการค้นหานี้", icon=ft.Icons.PERSON_OUTLINED)
            return

        cards = []
        for item in borrowers:
            avatar = ft.CircleAvatar(
                content=ft.Icon(ft.Icons.PERSON_OUTLINE, size=18, color=ft.Colors.GREEN_700),
                bgcolor=ft.Colors.GREEN_50,
                radius=18,
            )
            card_content = ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            avatar,
                            ft.Column(
                                controls=[
                                    ft.Text(item.full_name, weight=ft.FontWeight.BOLD, size=14, color=COLOR_TEXT_PRIMARY),
                                    ft.Text(item.borrower_code, size=12, color=COLOR_TEXT_SECONDARY),
                                ],
                                spacing=1,
                                tight=True,
                                expand=True,
                            ),
                        ],
                        spacing=10,
                    ),
                    ft.Divider(height=8, color=ft.Colors.GREY_200),
                    ft.Row(
                        controls=[
                            build_status_chip(item.status, self._translate_status(item.status)),
                        ],
                    ),
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.BUSINESS_OUTLINED, size=14, color=COLOR_TEXT_SECONDARY),
                            ft.Text(item.department or "ไม่มีหน่วยงาน", size=12, color=COLOR_TEXT_SECONDARY, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                        ],
                        spacing=4,
                    ),
                ],
                spacing=6,
                tight=True,
            )
            card = build_card(
                content=card_content,
                padding=12,
                width=240,
                on_click=lambda e, code=item.borrower_code, name=item.full_name, dept=item.department, email=item.email: self._select_borrower(code, name, dept, email),
            )
            cards.append(card)

        self.borrower_container.content = ft.Row(controls=cards, wrap=True, spacing=12, run_spacing=12)

    def _select_borrower(self, code: str, name: str, dept: str | None, email: str | None) -> None:
        self.borrower_code.value = code
        self.borrower_name.value = name
        self.borrower_department.value = dept or ""
        self.borrower_email.value = email or ""
        self.feedback.value = f"เลือกผู้ยืม {code} แล้ว"
        self.feedback.color = ft.Colors.BLUE_700
        update_control(self)

    def _handle_staff_search(self, e: ft.ControlEvent) -> None:
        self._render_staff()

    def _handle_staff_reset(self, e: ft.ControlEvent) -> None:
        self.staff_search.value = ""
        self._render_staff()

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
            self.feedback.value = "กรุณาใส่รหัสเจ้าหน้าที่และชื่อ"
            self.feedback.color = ft.Colors.RED_700
            update_control(self)
            return
        existing = self.service.get_staff(code)
        if existing is None:
            self.service.create_staff(code, name, email=email)
        else:
            self.service.update_staff(code, full_name=name, email=email)
        self.feedback.value = f"บันทึกเจ้าหน้าที่ {code} แล้ว"
        self.feedback.color = ft.Colors.GREEN_700
        self.staff_code.value = ""
        self.staff_name.value = ""
        self.staff_email.value = ""
        self._render_staff()
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
            self.service.create_borrower(code, name, department=department, email=email)
        else:
            self.service.update_borrower(code, full_name=name, department=department, email=email)
        self.feedback.value = f"บันทึกผู้ยืม {code} แล้ว"
        self.feedback.color = ft.Colors.GREEN_700
        self.borrower_code.value = ""
        self.borrower_name.value = ""
        self.borrower_department.value = ""
        self.borrower_email.value = ""
        self._render_borrowers()
        update_control(self)
