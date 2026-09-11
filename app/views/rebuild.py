"""The rebuilt, task-first workspace for the lending application.

The older view modules are kept as compatibility boundaries for existing
integrations and tests.  The application shell uses the views in this module:
one queue for staff work, one direct borrow flow, and one direct return flow.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Callable

import flet as ft

from app.components.common import (
    build_card,
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
from app.contracts import AppUser, Permission, has_permission
from app.database import bangkok_today
from app.theme import (
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
)
from app.views.dashboard import DashboardView as LegacyDashboardView
from app.views.history import HistoryView as LegacyHistoryView
from app.views.inventory import InventoryView as LegacyInventoryView
from app.views.loans import LoansView as LegacyLoansView
from app.views.my_loans import MyLoansView as LegacyMyLoansView
from app.services.fake_services import (
    FakeInventoryService,
    InventoryUnit,
    LoanRecord,
)


RouteAction = Callable[[str], None]


def _record_number(value: object) -> str:
    """Return the numeric part of fake or SQLite record ids."""
    raw = str(value or "")
    return raw.rsplit("-", 1)[-1]


def _staff_code_for_user(
    service: FakeInventoryService,
    current_user: AppUser | None,
) -> str | None:
    staff = service.list_staff(include_inactive=False)
    if current_user is not None and current_user.staff_id is not None:
        wanted = str(current_user.staff_id)
        match = next(
            (item for item in staff if str(item.id) == wanted or _record_number(item.id) == wanted),
            None,
        )
        if match is not None:
            return match.staff_code
    return staff[0].staff_code if staff else None


def _outstanding_units(loan: LoanRecord) -> list[str]:
    returned = set(loan.returned_unit_ids)
    return [unit_id for unit_id in loan.unit_ids if unit_id not in returned]


def _loan_state(loan: LoanRecord, *, today: date | None = None) -> str:
    if loan.status == "closed" or not _outstanding_units(loan):
        return "closed"
    today = today or bangkok_today()
    due = date.fromisoformat(loan.due_date)
    if due < today:
        return "overdue"
    if loan.status == "partial":
        return "partial"
    if due == today:
        return "today"
    if due <= today + timedelta(days=3):
        return "soon"
    return "active"


def _loan_state_label(state: str) -> str:
    return {
        "overdue": "เกินกำหนด",
        "today": "คืนวันนี้",
        "soon": "ใกล้ครบกำหนด",
        "partial": "คืนบางส่วน",
        "active": "กำลังยืม",
        "closed": "คืนครบแล้ว",
    }.get(state, state)


def _unit_label(service: FakeInventoryService, unit_id: str) -> str:
    unit = service.get_unit_by_id(unit_id)
    if unit is None:
        return unit_id
    return f"{unit.asset_code} — {unit.equipment_name}"


def _set_feedback(control: ft.Text, message: str, *, error: bool = False) -> None:
    control.value = message
    control.color = ft.Colors.RED_700 if error else ft.Colors.GREEN_700


class WorkspaceView(LegacyDashboardView):
    """Queue-first home page: show the work that needs attention today."""

    def __init__(
        self,
        service: FakeInventoryService | None = None,
        *,
        mobile: bool = False,
        current_user: AppUser | None = None,
        on_navigate: RouteAction | None = None,
    ) -> None:
        ft.Container.__init__(self, expand=True, padding=0)
        self.service = service or FakeInventoryService()
        self.mobile = mobile
        self.current_user = current_user
        self.on_navigate = on_navigate
        self.queue_container = ft.Container(expand=True)
        self.metric_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
        self.feedback = ft.Text("", size=13, color=COLOR_TEXT_SECONDARY)
        self._build_view()
        self.on_size_change = self._handle_resize

    def _go(self, route: str) -> None:
        if self.on_navigate is not None:
            self.on_navigate(route)

    def _build_view(self) -> None:
        display_name = self.current_user.display_name if self.current_user else "ผู้ปฏิบัติงาน"
        header = build_page_header(
            title=f"สวัสดี, {display_name}",
            subtitle="ดูงานที่ต้องจัดการ แล้วทำรายการให้เสร็จจากหน้านี้",
            icon=ft.Icons.WAVING_HAND_OUTLINED,
        )

        actions: list[ft.Control] = []
        if has_permission(self.current_user, Permission.MANAGE_LOANS):
            actions.extend(
                [
                    ft.Button(
                        "ยืมอุปกรณ์",
                        icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                        color=ft.Colors.WHITE,
                        bgcolor=COLOR_PRIMARY,
                        height=48,
                        on_click=lambda e: self._go("borrow"),
                    ),
                    ft.OutlinedButton(
                        "รับคืน",
                        icon=ft.Icons.REPLAY,
                        height=48,
                        on_click=lambda e: self._go("returns"),
                    ),
                ]
            )
        if actions:
            header = ft.Column(
                controls=[
                    header,
                    ft.Row(controls=actions, spacing=8, wrap=True),
                ],
                spacing=12,
                tight=True,
            )

        self.content = ft.Column(
            controls=[
                header,
                self.metric_row,
                build_card(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.TODAY, color=COLOR_PRIMARY, size=22),
                                    ft.Column(
                                        controls=[
                                            ft.Text(
                                                "คิวงานวันนี้",
                                                size=18,
                                                weight=ft.FontWeight.BOLD,
                                                color=COLOR_TEXT_PRIMARY,
                                            ),
                                            ft.Text(
                                                "รายการที่ควรจัดการก่อน เพื่อไม่ให้ของค้างหรือเลยกำหนด",
                                                size=13,
                                                color=COLOR_TEXT_SECONDARY,
                                            ),
                                        ],
                                        spacing=2,
                                        tight=True,
                                    ),
                                ],
                                spacing=10,
                            ),
                            self.queue_container,
                        ],
                        spacing=14,
                    ),
                    padding=20,
                ),
                self.feedback,
            ],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        self._render()

    def _render(self) -> None:
        units = self.service.list_units()
        loans = self.service.list_loans()
        today = bangkok_today()
        active_loans = [loan for loan in loans if _outstanding_units(loan)]
        due_today = [loan for loan in active_loans if _loan_state(loan, today=today) == "today"]
        overdue = [loan for loan in active_loans if _loan_state(loan, today=today) == "overdue"]
        maintenance = [unit for unit in units if unit.status == "maintenance"]
        lost = [unit for unit in units if unit.status == "reported_lost"]

        metrics = [
            ("พร้อมให้ยืม", sum(unit.status == "available" for unit in units), ft.Icons.CHECK_CIRCLE_OUTLINE, ft.Colors.GREEN_700, ft.Colors.GREEN_50),
            ("กำลังถูกยืม", len(active_loans), ft.Icons.HANDSHAKE_OUTLINED, ft.Colors.BLUE_700, ft.Colors.BLUE_50),
            ("ต้องคืนวันนี้", len(due_today), ft.Icons.EVENT, ft.Colors.ORANGE_800, ft.Colors.ORANGE_50),
            ("เกินกำหนด", len(overdue), ft.Icons.WARNING_AMBER_ROUNDED, ft.Colors.RED_700, ft.Colors.RED_50),
        ]
        self.metric_row.controls = [
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Icon(icon, color=color, size=22),
                            padding=10,
                            bgcolor=bgcolor,
                            border_radius=12,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(label, size=12, color=COLOR_TEXT_SECONDARY),
                                ft.Text(str(value), size=24, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                            ],
                            spacing=0,
                            tight=True,
                        ),
                    ],
                    spacing=10,
                ),
                padding=16,
                bgcolor=ft.Colors.SURFACE,
                border=ft.Border.all(1, COLOR_BORDER),
                border_radius=16,
                col={"xs": 12, "sm": 6, "md": 3},
            )
            for label, value, icon, color, bgcolor in metrics
        ]

        queue = sorted(
            active_loans,
            key=lambda loan: (
                {"overdue": 0, "today": 1, "soon": 2, "partial": 3, "active": 4}.get(
                    _loan_state(loan, today=today), 5
                ),
                loan.due_date,
            ),
        )
        if not queue:
            self.queue_container.content = build_state_view(
                "วันนี้ไม่มีงานค้าง",
                "รายการยืมทั้งหมดถูกคืนครบแล้ว หรือยังไม่มีการยืม",
                icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
            )
        else:
            cards: list[ft.Control] = []
            for loan in queue:
                state = _loan_state(loan, today=today)
                borrower = self.service.get_borrower(loan.borrower_code)
                borrower_label = (
                    f"{borrower.full_name} ({loan.borrower_code})"
                    if borrower is not None
                    else loan.borrower_code
                )
                outstanding = _outstanding_units(loan)
                cards.append(
                    build_data_card(
                        title=f"{borrower_label} · {loan.id}",
                        icon=ft.Icons.RECEIPT_LONG_OUTLINED,
                        status=(state, _loan_state_label(state)),
                        fields=[
                            ("ครบกำหนด", loan.due_date),
                            ("ค้างคืน", f"{len(outstanding)} / {len(loan.unit_ids)} ชิ้น"),
                            ("อุปกรณ์", ", ".join(_unit_label(self.service, item) for item in outstanding)),
                        ],
                        actions=[
                            ft.Button(
                                "รับคืนรายการนี้",
                                icon=ft.Icons.REPLAY,
                                color=ft.Colors.WHITE,
                                bgcolor=COLOR_PRIMARY,
                                expand=True,
                                on_click=lambda e: self._go("returns"),
                            )
                        ]
                        if has_permission(self.current_user, Permission.MANAGE_LOANS)
                        else None,
                        full_width_fields=["อุปกรณ์"],
                    )
                )
            self.queue_container.content = build_card_list(cards)

        if maintenance or lost:
            suffix = []
            if maintenance:
                suffix.append(f"รอซ่อม {len(maintenance)} ชิ้น")
            if lost:
                suffix.append(f"แจ้งหาย {len(lost)} ชิ้น")
            self.feedback.value = " · ".join(suffix)
            self.feedback.color = ft.Colors.ORANGE_800 if maintenance else ft.Colors.RED_700
        else:
            self.feedback.value = ""

    def _handle_resize(self, e: ft.LayoutSizeChangeEvent) -> None:
        handle_mobile_resize(self, self._build_view, e)


class QuickBorrowView(LegacyDashboardView):
    """A single-page borrowing flow with searchable people and multi-select units."""

    def __init__(
        self,
        service: FakeInventoryService | None = None,
        *,
        current_user: AppUser | None = None,
        notifier=None,
        mobile: bool = False,
    ) -> None:
        ft.Container.__init__(self, expand=True, padding=0)
        self.service = service or FakeInventoryService()
        self.current_user = current_user
        self.notifier = notifier
        self.mobile = mobile
        self.selected_borrower_code: str | None = None
        self.selected_unit_ids: list[str] = []
        self.borrower_search = ft.TextField(
            label="ค้นหาผู้ยืม",
            hint_text="พิมพ์ชื่อหรือรหัส เช่น BR-001",
            prefix_icon=ft.Icons.PERSON_SEARCH,
            height=52,
            on_change=self._handle_borrower_search,
        )
        self.borrower_results = ft.Container()
        self.unit_search = ft.TextField(
            label="ค้นหาอุปกรณ์",
            hint_text="พิมพ์ชื่อหรือรหัสทรัพย์สิน",
            prefix_icon=ft.Icons.SEARCH,
            height=52,
            on_change=self._handle_unit_search,
        )
        self.unit_results = ft.Container()
        self.borrow_date = ft.TextField(
            label="วันที่ยืม",
            value=bangkok_today().isoformat(),
            read_only=True,
            prefix_icon=ft.Icons.CALENDAR_TODAY,
        )
        self.due_date = ft.TextField(
            label="กำหนดคืน",
            value=(bangkok_today() + timedelta(days=3)).isoformat(),
            prefix_icon=ft.Icons.EVENT_REPEAT,
        )
        self.purpose = ft.TextField(
            label="วัตถุประสงค์ / หมายเหตุ (ไม่บังคับ)",
            hint_text="เช่น ยืมทำโครงงาน หรือใช้สอนวันที่...",
            multiline=True,
            min_lines=2,
            max_lines=4,
        )
        self.selected_summary = ft.Text("ยังไม่ได้เลือกผู้ยืมหรืออุปกรณ์", size=13, color=COLOR_TEXT_SECONDARY)
        self.feedback = ft.Text("", size=13, color=COLOR_TEXT_SECONDARY, weight=ft.FontWeight.W_500)
        self.save_button = ft.Button(
            "ยืนยันการยืม",
            icon=ft.Icons.CHECK_CIRCLE,
            color=ft.Colors.WHITE,
            bgcolor=COLOR_PRIMARY,
            height=52,
            expand=True,
            on_click=self._handle_borrow,
        )
        self._build_view()
        self.on_size_change = self._handle_resize

    def _build_view(self) -> None:
        if not has_permission(self.current_user, Permission.MANAGE_LOANS):
            self.content = build_state_view(
                "หน้านี้สำหรับเจ้าหน้าที่",
                "ให้เจ้าหน้าที่เป็นผู้บันทึกการรับ-จ่ายอุปกรณ์",
                icon=ft.Icons.LOCK_OUTLINE,
            )
            return
        header = build_page_header(
            title="ยืมอุปกรณ์",
            subtitle="เลือกผู้ยืม ค้นหาอุปกรณ์ ติ๊กหลายชิ้น แล้วกดยืนยันครั้งเดียว",
            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
        )
        staff_code = _staff_code_for_user(self.service, self.current_user)
        staff = self.service.get_staff(staff_code) if staff_code else None
        staff_label = f"บันทึกโดย {staff.full_name} ({staff.staff_code})" if staff else "ยังไม่มีเจ้าหน้าที่สำหรับบันทึก"
        due_presets = ft.Row(
            controls=[
                ft.Text("กำหนดเร็ว", size=12, color=COLOR_TEXT_SECONDARY),
                ft.OutlinedButton("+3 วัน", on_click=lambda e: self._set_due_days(3)),
                ft.OutlinedButton("+7 วัน", on_click=lambda e: self._set_due_days(7)),
                ft.OutlinedButton("+14 วัน", on_click=lambda e: self._set_due_days(14)),
            ],
            spacing=8,
            wrap=True,
        )
        left = ft.Column(
            controls=[
                build_card(
                    content=ft.Column(
                        controls=[
                            ft.Text("1 · ใครเป็นผู้ยืม", size=16, weight=ft.FontWeight.BOLD),
                            self.borrower_search,
                            self.borrower_results,
                        ],
                        spacing=12,
                        tight=True,
                    ),
                    padding=20,
                ),
                build_card(
                    content=ft.Column(
                        controls=[
                            ft.Text("2 · เลือกอุปกรณ์", size=16, weight=ft.FontWeight.BOLD),
                            ft.Text("เลือกได้มากกว่า 1 ชิ้นในรายการเดียว", size=12, color=COLOR_TEXT_SECONDARY),
                            self.unit_search,
                            self.unit_results,
                        ],
                        spacing=12,
                        tight=True,
                    ),
                    padding=20,
                ),
            ],
            spacing=16,
            expand=True,
        )
        right = ft.Column(
            controls=[
                build_card(
                    content=ft.Column(
                        controls=[
                            ft.Text("3 · กำหนดวันคืน", size=16, weight=ft.FontWeight.BOLD),
                            ft.Row(controls=[self.borrow_date, self.due_date], spacing=12),
                            due_presets,
                            self.purpose,
                        ],
                        spacing=12,
                        tight=True,
                    ),
                    padding=20,
                ),
                build_card(
                    content=ft.Column(
                        controls=[
                            ft.Text("ตรวจสอบก่อนบันทึก", size=16, weight=ft.FontWeight.BOLD),
                            ft.Text(staff_label, size=13, color=COLOR_TEXT_SECONDARY),
                            self.selected_summary,
                            self.feedback,
                            self.save_button,
                        ],
                        spacing=12,
                        tight=True,
                    ),
                    padding=20,
                    border_color=COLOR_PRIMARY,
                ),
            ],
            spacing=16,
            width=380 if not self.mobile else None,
        )
        self.content = ft.Column(
            controls=[
                header,
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(content=left, col={"xs": 12, "lg": 7}),
                        ft.Container(content=right, col={"xs": 12, "lg": 5}),
                    ],
                    spacing=16,
                    run_spacing=16,
                ),
            ],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        self._render_borrowers()
        self._render_units()
        self._update_summary()

    def _set_due_days(self, days: int) -> None:
        try:
            start = date.fromisoformat(self.borrow_date.value or "")
        except ValueError:
            start = bangkok_today()
        self.due_date.value = (start + timedelta(days=days)).isoformat()
        update_control(self)

    def _render_borrowers(self) -> None:
        query = (self.borrower_search.value or "").strip().casefold()
        borrowers = self.service.list_borrowers()
        if query:
            borrowers = [
                item
                for item in borrowers
                if query in item.borrower_code.casefold()
                or query in item.full_name.casefold()
                or query in (item.department or "").casefold()
            ]
        if not borrowers:
            self.borrower_results.content = ft.Text("ไม่พบผู้ยืมที่ใช้งานได้", size=13, color=COLOR_TEXT_SECONDARY)
            return
        self.borrower_results.content = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.PERSON_OUTLINE, color=COLOR_PRIMARY),
                            ft.Column(
                                controls=[
                                    ft.Text(item.full_name, weight=ft.FontWeight.W_600),
                                    ft.Text(f"{item.borrower_code} · {item.department or 'ไม่ระบุหน่วยงาน'}", size=12, color=COLOR_TEXT_SECONDARY),
                                ],
                                spacing=2,
                                tight=True,
                                expand=True,
                            ),
                            ft.Button(
                                "เลือกแล้ว" if item.borrower_code == self.selected_borrower_code else "เลือก",
                                icon=ft.Icons.CHECK if item.borrower_code == self.selected_borrower_code else ft.Icons.ARROW_FORWARD,
                                color=ft.Colors.WHITE if item.borrower_code == self.selected_borrower_code else COLOR_PRIMARY,
                                bgcolor=COLOR_PRIMARY if item.borrower_code == self.selected_borrower_code else None,
                                on_click=lambda e, code=item.borrower_code: self._select_borrower(code),
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=12,
                    bgcolor=ft.Colors.BLUE_50 if item.borrower_code == self.selected_borrower_code else ft.Colors.SURFACE,
                    border=ft.Border.all(1, COLOR_PRIMARY if item.borrower_code == self.selected_borrower_code else COLOR_BORDER),
                    border_radius=12,
                )
                for item in borrowers[:12]
            ],
            spacing=8,
            tight=True,
        )

    def _render_units(self) -> None:
        query = (self.unit_search.value or "").strip()
        units = self.service.search_units(query or None, status="available")
        if not units:
            self.unit_results.content = build_state_view(
                "ไม่พบอุปกรณ์พร้อมให้ยืม",
                "ลองเปลี่ยนคำค้น หรือเช็กว่าสถานะอุปกรณ์เป็นพร้อมใช้งาน",
                icon=ft.Icons.INVENTORY_2_OUTLINED,
            )
            return
        self.unit_results.content = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Checkbox(
                                label=f"{unit.asset_code} · {unit.equipment_name}",
                                value=unit.id in self.selected_unit_ids,
                                on_change=lambda e, unit_id=unit.id: self._toggle_unit(unit_id),
                                expand=True,
                            ),
                            ft.Text(unit.location, size=11, color=COLOR_TEXT_SECONDARY),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=8,
                    border=ft.Border.all(1, COLOR_PRIMARY if unit.id in self.selected_unit_ids else COLOR_BORDER),
                    bgcolor=ft.Colors.BLUE_50 if unit.id in self.selected_unit_ids else ft.Colors.SURFACE,
                    border_radius=10,
                )
                for unit in units[:40]
            ],
            spacing=6,
            tight=True,
        )

    def _select_borrower(self, code: str) -> None:
        self.selected_borrower_code = code
        self._render_borrowers()
        self._update_summary()
        update_control(self)

    def _toggle_unit(self, unit_id: str) -> None:
        if unit_id in self.selected_unit_ids:
            self.selected_unit_ids.remove(unit_id)
        else:
            self.selected_unit_ids.append(unit_id)
        self._render_units()
        self._update_summary()
        update_control(self)

    def _update_summary(self) -> None:
        borrower = self.service.get_borrower(self.selected_borrower_code or "") if self.selected_borrower_code else None
        borrower_text = borrower.full_name if borrower else "ยังไม่ได้เลือกผู้ยืม"
        unit_text = (
            ", ".join(_unit_label(self.service, unit_id) for unit_id in self.selected_unit_ids)
            if self.selected_unit_ids
            else "ยังไม่ได้เลือกอุปกรณ์"
        )
        self.selected_summary.value = f"ผู้ยืม: {borrower_text}\nอุปกรณ์ {len(self.selected_unit_ids)} ชิ้น: {unit_text}"
        self.selected_summary.color = COLOR_PRIMARY if borrower and self.selected_unit_ids else COLOR_TEXT_SECONDARY

    def _handle_borrower_search(self, e: ft.ControlEvent | None) -> None:
        self._render_borrowers()
        update_control(self)

    def _handle_unit_search(self, e: ft.ControlEvent | None) -> None:
        self._render_units()
        update_control(self)

    def _handle_borrow(self, e: ft.ControlEvent | None) -> None:
        if not has_permission(self.current_user, Permission.MANAGE_LOANS):
            _set_feedback(self.feedback, "คุณไม่มีสิทธิ์บันทึกการยืม", error=True)
            update_control(self)
            return
        staff_code = _staff_code_for_user(self.service, self.current_user)
        if not self.selected_borrower_code:
            _set_feedback(self.feedback, "เลือกผู้ยืมก่อนบันทึก", error=True)
            update_control(self)
            return
        if not self.selected_unit_ids:
            _set_feedback(self.feedback, "เลือกอุปกรณ์อย่างน้อย 1 ชิ้น", error=True)
            update_control(self)
            return
        if staff_code is None:
            _set_feedback(self.feedback, "ยังไม่มีเจ้าหน้าที่สำหรับบันทึกรายการ", error=True)
            update_control(self)
            return
        try:
            borrow_date = date.fromisoformat(self.borrow_date.value or "")
            due_date = date.fromisoformat(self.due_date.value or "")
        except ValueError:
            _set_feedback(self.feedback, "รูปแบบวันที่ต้องเป็น YYYY-MM-DD", error=True)
            update_control(self)
            return
        if due_date < borrow_date:
            _set_feedback(self.feedback, "กำหนดคืนต้องไม่ก่อนวันที่ยืม", error=True)
            update_control(self)
            return
        result = self.service.create_and_confirm_borrow(
            borrower_code=self.selected_borrower_code,
            staff_code=staff_code,
            unit_ids=list(self.selected_unit_ids),
            borrow_date=borrow_date.isoformat(),
            due_date=due_date.isoformat(),
            purpose=(self.purpose.value or "").strip(),
        )
        if result is None:
            _set_feedback(self.feedback, "บันทึกไม่สำเร็จ อุปกรณ์อาจถูกยืมไปแล้ว กรุณารีเฟรชแล้วลองใหม่", error=True)
            update_control(self)
            return
        if self.notifier is not None:
            try:
                self.notifier.notify_loan_created(
                    borrower_code=result.borrower_code,
                    transaction_code=result.id,
                    due_date=result.due_date,
                    unit_count=len(result.unit_ids),
                )
            except Exception:
                pass
        _set_feedback(self.feedback, f"บันทึกการยืม {result.id} เรียบร้อยแล้ว")
        self.selected_unit_ids = []
        self.unit_search.value = ""
        self.purpose.value = ""
        self._render_units()
        self._update_summary()
        update_control(self)

    def _handle_resize(self, e: ft.LayoutSizeChangeEvent) -> None:
        handle_mobile_resize(self, self._build_view, e)


class QuickReturnView(LegacyLoansView):
    """Return work queue with all outstanding items preselected."""

    def __init__(
        self,
        service: FakeInventoryService | None = None,
        *,
        mobile: bool = False,
        current_user: AppUser | None = None,
        notifier=None,
    ) -> None:
        ft.Container.__init__(self, expand=True, padding=0)
        self.service = service or FakeInventoryService()
        self.mobile = mobile
        self.current_user = current_user
        self.notifier = notifier
        self.selected_loan: LoanRecord | None = None
        self.selected_unit_ids: list[str] = []
        self.search_field = ft.TextField(
            label="ค้นหาผู้ยืม รหัสรายการ หรืออุปกรณ์",
            hint_text="เช่น สมชาย, BR-001, LOAN-001 หรือ AST-001",
            prefix_icon=ft.Icons.SEARCH,
            height=52,
            on_change=self._handle_search,
        )
        self.filter_dropdown = ft.Dropdown(
            label="แสดง",
            value="all",
            options=[
                ft.dropdown.Option("all", "งานที่ยังไม่ปิด"),
                ft.dropdown.Option("overdue", "เกินกำหนดก่อน"),
                ft.dropdown.Option("today", "ครบกำหนดวันนี้"),
                ft.dropdown.Option("partial", "คืนบางส่วน"),
            ],
            height=52,
            on_select=self._handle_filter,
        )
        self.loan_container = ft.Container(expand=True)
        self.detail_container = ft.Container(expand=True)
        self.return_action_dropdown = ft.Dropdown(
            label="ผลลัพธ์",
            value="returned",
            options=[
                ft.dropdown.Option("returned", "รับคืน — พร้อมใช้"),
                ft.dropdown.Option("maintenance", "รับคืน — ส่งซ่อม"),
                ft.dropdown.Option("reported_lost", "ยังไม่ได้คืน — แจ้งหาย"),
            ],
            on_select=self._handle_return_action,
        )
        self.receiving_staff_dropdown = ft.Dropdown(label="ผู้รับคืน", options=[])
        self.return_location_dropdown = ft.Dropdown(label="เก็บไว้ที่", options=[])
        self.return_notes = ft.TextField(
            label="สภาพ / หมายเหตุ (ไม่บังคับ)",
            hint_text="เช่น ครบชุด, มีรอยเล็กน้อย, สายชาร์จไม่ครบ",
            multiline=True,
            min_lines=2,
            max_lines=4,
        )
        self.feedback = ft.Text("", size=13, color=COLOR_TEXT_SECONDARY, weight=ft.FontWeight.W_500)
        self._fill_staff_and_locations()
        self._build_view()
        self.on_size_change = self._handle_resize

    def _fill_staff_and_locations(self) -> None:
        staff = self.service.list_staff()
        self.receiving_staff_dropdown.options = [
            ft.dropdown.Option(item.staff_code, f"{item.full_name} ({item.staff_code})")
            for item in staff
        ]
        preferred = _staff_code_for_user(self.service, self.current_user)
        self.receiving_staff_dropdown.value = preferred or (staff[0].staff_code if staff else None)
        locations = self.service.list_locations()
        self.return_location_dropdown.options = [
            ft.dropdown.Option(item.id, item.label) for item in locations
        ]
        self.return_location_dropdown.value = locations[0].id if locations else None

    def _build_view(self) -> None:
        if not has_permission(self.current_user, Permission.MANAGE_LOANS):
            self.content = build_state_view(
                "หน้านี้สำหรับเจ้าหน้าที่",
                "ให้เจ้าหน้าที่เป็นผู้บันทึกการรับ-จ่ายอุปกรณ์",
                icon=ft.Icons.LOCK_OUTLINE,
            )
            return
        header = build_page_header(
            title="รับคืนอุปกรณ์",
            subtitle="เลือกงานที่นำมาคืน ระบบเลือกของที่ยังค้างให้อัตโนมัติ",
            icon=ft.Icons.REPLAY,
        )
        filters = build_filter_bar(
            search_control=self.search_field,
            action_controls=[self.filter_dropdown, ft.OutlinedButton("รีเฟรช", icon=ft.Icons.REFRESH, height=52, on_click=self._handle_refresh)],
        )
        self.content = ft.Column(
            controls=[
                header,
                filters,
                self.feedback,
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(content=self.loan_container, col={"xs": 12, "lg": 6}),
                        ft.Container(content=self.detail_container, col={"xs": 12, "lg": 6}),
                    ],
                    spacing=16,
                    run_spacing=16,
                ),
            ],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        self._render_loans()
        self._render_detail()

    def _all_active_loans(self) -> list[LoanRecord]:
        return [loan for loan in self.service.list_loans() if _outstanding_units(loan)]

    def _matches(self, loan: LoanRecord, query: str) -> bool:
        if not query:
            return True
        borrower = self.service.get_borrower(loan.borrower_code)
        values = [loan.id, loan.borrower_code, loan.purpose]
        if borrower is not None:
            values.extend([borrower.full_name, borrower.department or ""])
        values.extend(_unit_label(self.service, unit_id) for unit_id in _outstanding_units(loan))
        return any(query in str(value).casefold() for value in values)

    def _render_loans(self) -> None:
        loans = self._all_active_loans()
        query = (self.search_field.value or "").strip().casefold()
        selected_filter = self.filter_dropdown.value or "all"
        today = bangkok_today()
        if query:
            loans = [loan for loan in loans if self._matches(loan, query)]
        if selected_filter != "all":
            loans = [
                loan
                for loan in loans
                if (
                    _loan_state(loan, today=today) == selected_filter
                    or selected_filter == "partial" and loan.status == "partial"
                )
            ]
        loans.sort(
            key=lambda loan: (
                {"overdue": 0, "today": 1, "soon": 2, "partial": 3, "active": 4}.get(_loan_state(loan, today=today), 5),
                loan.due_date,
            )
        )
        if not loans:
            self.loan_container.content = build_state_view(
                "ไม่มีรายการที่ต้องรับคืน",
                "เปลี่ยนตัวกรองหรือค้นหาด้วยชื่อผู้ยืม / รหัสอุปกรณ์",
                icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
            )
            return
        cards = []
        for loan in loans:
            state = _loan_state(loan, today=today)
            borrower = self.service.get_borrower(loan.borrower_code)
            name = borrower.full_name if borrower is not None else loan.borrower_code
            outstanding = _outstanding_units(loan)
            cards.append(
                build_data_card(
                    title=f"{name} · {loan.id}",
                    icon=ft.Icons.RECEIPT_LONG_OUTLINED,
                    status=(state, _loan_state_label(state)),
                    fields=[
                        ("ครบกำหนด", loan.due_date),
                        ("ค้างคืน", f"{len(outstanding)} ชิ้น"),
                        ("รหัสผู้ยืม", loan.borrower_code),
                        ("อุปกรณ์", ", ".join(_unit_label(self.service, item) for item in outstanding)),
                    ],
                    actions=[
                        ft.Button(
                            "เลือกงานนี้",
                            icon=ft.Icons.ARROW_FORWARD,
                            color=ft.Colors.WHITE,
                            bgcolor=COLOR_PRIMARY,
                            expand=True,
                            on_click=lambda e, selected=loan: self._select_loan(selected),
                        )
                    ],
                    full_width_fields=["อุปกรณ์"],
                )
            )
        self.loan_container.content = build_card_list(cards)

    def _render_detail(self) -> None:
        loan = self.selected_loan
        if loan is None:
            self.detail_container.content = build_state_view(
                "เลือกงานจากด้านซ้าย",
                "ระบบจะติ๊กอุปกรณ์ที่ยังค้างให้พร้อมรับคืนทันที",
                icon=ft.Icons.POINT_OF_SALE_OUTLINED,
            )
            return
        outstanding = _outstanding_units(loan)
        borrower = self.service.get_borrower(loan.borrower_code)
        borrower_label = borrower.full_name if borrower is not None else loan.borrower_code
        unit_controls = [
            ft.Checkbox(
                label=_unit_label(self.service, unit_id),
                value=unit_id in self.selected_unit_ids,
                on_change=lambda e, selected=unit_id: self._toggle_return_unit(selected),
            )
            for unit_id in outstanding
        ]
        action = self.return_action_dropdown.value or "returned"
        location_control: ft.Control = self.return_location_dropdown
        if action == "reported_lost":
            location_control = ft.Text("รายการนี้จะเปลี่ยนเป็นแจ้งหาย และไม่ต้องเลือกจุดเก็บ", size=12, color=ft.Colors.RED_700)
        self.detail_container.content = build_card(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.RECEIPT_LONG, color=COLOR_PRIMARY, size=22),
                            ft.Column(
                                controls=[
                                    ft.Text("รายละเอียดการรับคืน", size=18, weight=ft.FontWeight.BOLD),
                                    ft.Text(f"{borrower_label} · ครบกำหนด {loan.due_date}", size=13, color=COLOR_TEXT_SECONDARY),
                                ],
                                spacing=2,
                                tight=True,
                                expand=True,
                            ),
                            build_status_chip(_loan_state(loan), _loan_state_label(_loan_state(loan))),
                        ],
                        spacing=10,
                    ),
                    ft.Divider(height=1),
                    ft.Text("อุปกรณ์ที่จะรับคืน", size=15, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        controls=[
                            ft.Text(f"เลือกแล้ว {len(self.selected_unit_ids)} / {len(outstanding)} ชิ้น", size=13, color=COLOR_TEXT_SECONDARY, expand=True),
                            ft.TextButton("เลือกทั้งหมด", on_click=lambda e: self._select_all_return_units()),
                            ft.TextButton("ล้าง", on_click=lambda e: self._clear_return_units()),
                        ],
                        spacing=4,
                    ),
                    ft.Column(controls=unit_controls, spacing=4, tight=True),
                    self.return_action_dropdown,
                    location_control,
                    self.receiving_staff_dropdown,
                    self.return_notes,
                    ft.Button(
                        "ยืนยันรับคืน",
                        icon=ft.Icons.CHECK_CIRCLE,
                        color=ft.Colors.WHITE,
                        bgcolor=COLOR_PRIMARY,
                        height=52,
                        expand=True,
                        on_click=self._handle_confirm_return,
                    ),
                ],
                spacing=12,
                tight=True,
            ),
            padding=20,
            border_color=COLOR_PRIMARY,
        )

    def _select_loan(self, loan: LoanRecord) -> None:
        self.selected_loan = loan
        self.selected_unit_ids = _outstanding_units(loan)
        self.return_action_dropdown.value = "returned"
        self.return_notes.value = ""
        self._render_loans()
        self._render_detail()
        update_control(self)

    def _toggle_return_unit(self, unit_id: str) -> None:
        if unit_id in self.selected_unit_ids:
            self.selected_unit_ids.remove(unit_id)
        else:
            self.selected_unit_ids.append(unit_id)
        self._render_detail()
        update_control(self)

    def _select_all_return_units(self) -> None:
        self.selected_unit_ids = _outstanding_units(self.selected_loan) if self.selected_loan else []
        self._render_detail()
        update_control(self)

    def _clear_return_units(self) -> None:
        self.selected_unit_ids = []
        self._render_detail()
        update_control(self)

    def _handle_return_action(self, e: ft.ControlEvent | None) -> None:
        self._render_detail()
        update_control(self)

    def _handle_search(self, e: ft.ControlEvent | None) -> None:
        self._render_loans()
        update_control(self)

    def _handle_filter(self, e: ft.ControlEvent | None) -> None:
        self._render_loans()
        update_control(self)

    def _handle_refresh(self, e: ft.ControlEvent | None) -> None:
        self.selected_loan = None
        self.selected_unit_ids = []
        self.search_field.value = ""
        self.filter_dropdown.value = "all"
        self._fill_staff_and_locations()
        self._render_loans()
        self._render_detail()
        update_control(self)

    def _handle_confirm_return(self, e: ft.ControlEvent | None) -> None:
        if not has_permission(self.current_user, Permission.MANAGE_LOANS):
            _set_feedback(self.feedback, "คุณไม่มีสิทธิ์บันทึกการคืน", error=True)
            update_control(self)
            return
        if self.selected_loan is None:
            _set_feedback(self.feedback, "เลือกรายการที่นำมาคืนก่อน", error=True)
            update_control(self)
            return
        if not self.selected_unit_ids:
            _set_feedback(self.feedback, "เลือกอุปกรณ์ที่จะคืนอย่างน้อย 1 ชิ้น", error=True)
            update_control(self)
            return
        action = self.return_action_dropdown.value or "returned"
        if not self.receiving_staff_dropdown.value:
            _set_feedback(self.feedback, "ยังไม่มีผู้รับคืน", error=True)
            update_control(self)
            return
        if action != "reported_lost" and not self.return_location_dropdown.value:
            _set_feedback(self.feedback, "เลือกจุดเก็บหลังคืนก่อน", error=True)
            update_control(self)
            return
        result = self.service.return_loan_units(
            self.selected_loan.id,
            list(self.selected_unit_ids),
            action,
            condition=(self.return_notes.value or "").strip() or None,
            staff_code=self.receiving_staff_dropdown.value,
            location_id=self.return_location_dropdown.value,
        )
        if result is None:
            _set_feedback(self.feedback, "บันทึกไม่สำเร็จ รายการอาจถูกแก้ไขแล้ว กรุณารีเฟรช", error=True)
            update_control(self)
            return
        returned_count = len(self.selected_unit_ids)
        if self.notifier is not None:
            try:
                self.notifier.notify_loan_returned(
                    borrower_code=result.borrower_code,
                    transaction_code=result.id,
                    returned_count=returned_count,
                )
            except Exception:
                pass
        _set_feedback(self.feedback, f"รับคืน {returned_count} ชิ้นจาก {result.id} เรียบร้อยแล้ว")
        self.selected_loan = None if result.status == "closed" else result
        self.selected_unit_ids = [] if self.selected_loan is None else _outstanding_units(result)
        self.return_notes.value = ""
        self._render_loans()
        self._render_detail()
        update_control(self)

    def _handle_resize(self, e: ft.LayoutSizeChangeEvent) -> None:
        handle_mobile_resize(self, self._build_view, e)


class InventoryWorkspaceView(LegacyInventoryView):
    """Inventory page with everyday search plus contained admin actions."""

    def __init__(
        self,
        service: FakeInventoryService | None = None,
        *,
        mobile: bool = False,
        current_user: AppUser | None = None,
    ) -> None:
        ft.Container.__init__(self, expand=True, padding=0)
        self.service = service or FakeInventoryService()
        self.mobile = mobile
        self.current_user = current_user
        self.search_field = ft.TextField(
            label="ค้นหาอุปกรณ์",
            hint_text="ชื่อหรือรหัสทรัพย์สิน",
            prefix_icon=ft.Icons.SEARCH,
            height=52,
            on_change=self._handle_search,
        )
        self.status_dropdown = ft.Dropdown(
            label="สถานะ",
            value="all",
            height=52,
            options=[
                ft.dropdown.Option("all", "ทุกสถานะ"),
                ft.dropdown.Option("available", "พร้อมใช้งาน"),
                ft.dropdown.Option("borrowed", "ถูกยืม"),
                ft.dropdown.Option("maintenance", "กำลังซ่อม"),
                ft.dropdown.Option("reported_lost", "แจ้งหาย"),
                ft.dropdown.Option("retired", "ปลดระวาง"),
            ],
            on_select=self._handle_search,
        )
        self.category_dropdown = ft.Dropdown(label="หมวดหมู่", value="all", height=52, on_select=self._handle_search)
        self.unit_container = ft.Container(expand=True)
        self.summary = ft.ResponsiveRow(spacing=8, run_spacing=8)
        self.feedback = ft.Text("", size=13, color=COLOR_TEXT_SECONDARY)
        self.add_name = ft.TextField(label="ชื่ออุปกรณ์")
        self.add_asset_code = ft.TextField(label="รหัสทรัพย์สิน", hint_text="เช่น CAM-001")
        self.add_category = ft.Dropdown(label="หมวดหมู่", options=[])
        self.add_location = ft.TextField(label="จุดเก็บ", hint_text="เช่น ห้องเก็บของ ชั้น 1")
        self.add_dialog = build_form_dialog(
            title="เพิ่มอุปกรณ์",
            icon=ft.Icons.ADD_BOX_OUTLINED,
            content=ft.Column(controls=[self.add_asset_code, self.add_name, self.add_category, self.add_location], spacing=12, tight=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            save_label="เพิ่มเข้าคลัง",
            on_save=self._save_new_unit,
            on_cancel=lambda e: close_dialog(self, self.add_dialog),
        )
        self.manage_unit = ft.Dropdown(label="อุปกรณ์", options=[])
        self.manage_action = ft.Dropdown(
            label="การจัดการ",
            value="relocate",
            options=[
                ft.dropdown.Option("relocate", "ย้ายจุดเก็บ"),
                ft.dropdown.Option("maintenance", "ซ่อมเสร็จแล้ว"),
                ft.dropdown.Option("retired", "ปลดระวาง"),
                ft.dropdown.Option("lost_recovered", "พบของที่แจ้งหาย"),
                ft.dropdown.Option("lost_closed", "ปิดเคสของหาย"),
            ],
        )
        self.manage_location = ft.TextField(label="จุดเก็บใหม่", hint_text="จำเป็นเมื่อย้าย/พบของ")
        self.manage_reason = ft.TextField(label="เหตุผล", multiline=True, min_lines=2)
        self.manage_dialog = build_form_dialog(
            title="จัดการอุปกรณ์",
            icon=ft.Icons.TUNE,
            content=ft.Column(controls=[self.manage_unit, self.manage_action, self.manage_location, self.manage_reason], spacing=12, tight=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            save_label="บันทึกการเปลี่ยนแปลง",
            on_save=self._save_management,
            on_cancel=lambda e: close_dialog(self, self.manage_dialog),
        )
        self._refresh_options()
        self._build_view()
        self.on_size_change = self._handle_resize

    def _is_admin(self) -> bool:
        return has_permission(self.current_user, Permission.MANAGE_INVENTORY)

    def _refresh_options(self) -> None:
        categories = sorted({item.category for item in self.service.list_units() if item.category})
        self.category_dropdown.options = [ft.dropdown.Option("all", "ทุกหมวดหมู่")] + [ft.dropdown.Option(item, item) for item in categories]
        category_records = self.service.list_categories()
        self.add_category.options = [ft.dropdown.Option(item.id, item.name) for item in category_records]
        units = self.service.list_units()
        self.manage_unit.options = [ft.dropdown.Option(item.id, f"{item.asset_code} — {item.equipment_name}") for item in units]

    def _build_view(self) -> None:
        header = build_page_header(
            title="คลังอุปกรณ์",
            subtitle="ค้นหาได้จากชื่อหรือรหัสทรัพย์สิน ทุกชิ้นมีสถานะและจุดเก็บของตัวเอง",
            icon=ft.Icons.INVENTORY_2,
        )
        actions: list[ft.Control] = [ft.OutlinedButton("รีเฟรช", icon=ft.Icons.REFRESH, height=52, on_click=self._handle_refresh)]
        if self._is_admin():
            actions.extend([
                ft.Button("เพิ่มอุปกรณ์", icon=ft.Icons.ADD, color=ft.Colors.WHITE, bgcolor=COLOR_PRIMARY, height=52, on_click=self._open_add_dialog),
                ft.OutlinedButton("จัดการสถานะ", icon=ft.Icons.TUNE, height=52, on_click=self._open_manage_dialog),
            ])
        filters = build_filter_bar(search_control=self.search_field, action_controls=[self.status_dropdown, self.category_dropdown, *actions])
        self.content = ft.Column(
            controls=[header, self.summary, filters, self.feedback, self.unit_container],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        self._render()

    def _render(self) -> None:
        query = (self.search_field.value or "").strip()
        status = None if self.status_dropdown.value in (None, "all") else self.status_dropdown.value
        category = None if self.category_dropdown.value in (None, "all") else self.category_dropdown.value
        units = self.service.search_units(query or None, status=status, category=category)
        all_units = self.service.list_units()
        self.summary.controls = [
            ft.Container(
                content=ft.Row(controls=[ft.Text(label, size=12, color=COLOR_TEXT_SECONDARY), ft.Text(str(sum(item.status == state for item in all_units)), size=20, weight=ft.FontWeight.BOLD)], spacing=8),
                padding=12,
                bgcolor=bgcolor,
                border_radius=12,
                col={"xs": 6, "sm": 3},
            )
            for label, state, bgcolor in [
                ("พร้อมใช้", "available", ft.Colors.GREEN_50),
                ("ถูกยืม", "borrowed", ft.Colors.BLUE_50),
                ("กำลังซ่อม", "maintenance", ft.Colors.ORANGE_50),
                ("แจ้งหาย", "reported_lost", ft.Colors.RED_50),
            ]
        ]
        if not units:
            self.unit_container.content = build_state_view("ไม่พบอุปกรณ์", "ลองเปลี่ยนคำค้นหาหรือตัวกรอง", icon=ft.Icons.INVENTORY_2_OUTLINED)
            return
        if self.mobile:
            self.unit_container.content = build_card_list([self._unit_card(unit) for unit in units])
            return
        table = ft.DataTable(
            columns=[ft.DataColumn(ft.Text("รหัส"), expand=2), ft.DataColumn(ft.Text("อุปกรณ์"), expand=3), ft.DataColumn(ft.Text("สถานะ"), expand=2), ft.DataColumn(ft.Text("จุดเก็บ"), expand=3), ft.DataColumn(ft.Text("จัดการ"), expand=1)],
            rows=[
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(unit.asset_code, weight=ft.FontWeight.W_600)),
                    ft.DataCell(ft.Text(unit.equipment_name)),
                    ft.DataCell(build_status_chip(unit.status, self._status_label(unit.status))),
                    ft.DataCell(ft.Text(unit.location)),
                    ft.DataCell(ft.TextButton("จัดการ", on_click=lambda e, selected=unit: self._open_manage_dialog(selected))),
                ])
                for unit in units
            ],
            column_spacing=18,
            horizontal_lines=ft.BorderSide(1, COLOR_BORDER),
        )
        self.unit_container.content = build_table_surface(table, table_width=1000, on_resized=lambda width: None)

    def _unit_card(self, unit: InventoryUnit) -> ft.Container:
        return build_data_card(
            title=unit.asset_code,
            icon=ft.Icons.INVENTORY_2_OUTLINED,
            status=(unit.status, self._status_label(unit.status)),
            fields=[("อุปกรณ์", unit.equipment_name), ("จุดเก็บ", unit.location), ("หมวดหมู่", unit.category or "-")],
            actions=[ft.Button("จัดการ", icon=ft.Icons.TUNE, on_click=lambda e, selected=unit: self._open_manage_dialog(selected))] if self._is_admin() else None,
        )

    @staticmethod
    def _status_label(status: str) -> str:
        return {"available": "พร้อมใช้งาน", "borrowed": "ถูกยืม", "maintenance": "กำลังซ่อม", "reported_lost": "แจ้งหาย", "retired": "ปลดระวาง"}.get(status, status)

    def _handle_search(self, e: ft.ControlEvent | None) -> None:
        self._render()
        update_control(self)

    def _handle_refresh(self, e: ft.ControlEvent | None) -> None:
        self.search_field.value = ""
        self.status_dropdown.value = "all"
        self.category_dropdown.value = "all"
        self._refresh_options()
        self._render()
        update_control(self)

    def _open_add_dialog(self, e: ft.ControlEvent | None) -> None:
        if not self._is_admin():
            _set_feedback(self.feedback, "คุณไม่มีสิทธิ์จัดการคลัง", error=True)
            return
        self.add_asset_code.value = ""
        self.add_name.value = ""
        self.add_location.value = ""
        if self.add_category.options:
            self.add_category.value = self.add_category.options[0].key
        open_dialog(self, self.add_dialog)

    def _save_new_unit(self, e: ft.ControlEvent | None) -> None:
        if not self._is_admin():
            _set_feedback(self.feedback, "คุณไม่มีสิทธิ์จัดการคลัง", error=True)
            return
        name = (self.add_name.value or "").strip()
        asset_code = (self.add_asset_code.value or "").strip()
        location = (self.add_location.value or "").strip()
        category_id = self.add_category.value or ""
        if not name or not asset_code or not location or not category_id:
            _set_feedback(self.feedback, "กรอกชื่อ รหัส หมวดหมู่ และจุดเก็บให้ครบ", error=True)
            return
        saved = self.service.create_inventory_item(name=name, category_id=category_id, asset_code=asset_code, location=location)
        if saved is None:
            _set_feedback(self.feedback, "เพิ่มไม่สำเร็จ รหัสทรัพย์สินอาจซ้ำ", error=True)
            return
        _set_feedback(self.feedback, f"เพิ่ม {saved.asset_code} เข้าคลังแล้ว")
        close_dialog(self, self.add_dialog)
        self._refresh_options()
        self._render()

    def _open_manage_dialog(self, unit: InventoryUnit | None = None) -> None:
        if not self._is_admin():
            _set_feedback(self.feedback, "คุณไม่มีสิทธิ์จัดการคลัง", error=True)
            return
        if unit is not None:
            self.manage_unit.value = unit.id
        if self.manage_unit.value is None and self.manage_unit.options:
            self.manage_unit.value = self.manage_unit.options[0].key
        self.manage_location.value = ""
        self.manage_reason.value = ""
        open_dialog(self, self.manage_dialog)

    def _save_management(self, e: ft.ControlEvent | None) -> None:
        if not self._is_admin():
            _set_feedback(self.feedback, "คุณไม่มีสิทธิ์จัดการคลัง", error=True)
            return
        unit_id = self.manage_unit.value
        action = self.manage_action.value or "relocate"
        if not unit_id:
            _set_feedback(self.feedback, "เลือกอุปกรณ์ก่อน", error=True)
            return
        if action in {"relocate", "maintenance", "lost_recovered"} and not (self.manage_location.value or "").strip():
            _set_feedback(self.feedback, "ระบุจุดเก็บใหม่ก่อน", error=True)
            return
        saved = self.service.update_unit_status(unit_id, action, location=(self.manage_location.value or "").strip() or None, reason=(self.manage_reason.value or "").strip() or None)
        if saved is None:
            _set_feedback(self.feedback, "เปลี่ยนสถานะไม่สำเร็จ ตรวจสอบสถานะปัจจุบันของอุปกรณ์", error=True)
            return
        _set_feedback(self.feedback, f"อัปเดต {saved.asset_code} แล้ว")
        close_dialog(self, self.manage_dialog)
        self._refresh_options()
        self._render()

    def _handle_resize(self, e: ft.LayoutSizeChangeEvent) -> None:
        handle_mobile_resize(self, self._build_view, e)


class MyLoansWorkspaceView(LegacyMyLoansView):
    """Borrower view focused on what is currently in the person's hands."""

    def __init__(
        self,
        service: FakeInventoryService | None = None,
        *,
        current_user: AppUser | None = None,
        mobile: bool = False,
    ) -> None:
        ft.Container.__init__(self, expand=True, padding=0)
        self.service = service or FakeInventoryService()
        self.current_user = current_user
        self.mobile = mobile
        self.search_field = ft.TextField(label="ค้นหารายการ", hint_text="รหัสรายการหรืออุปกรณ์", prefix_icon=ft.Icons.SEARCH, height=52, on_change=self._handle_search)
        self.loan_container = ft.Container(expand=True)
        self.feedback = ft.Text("", size=13, color=COLOR_TEXT_SECONDARY)
        self._build_view()
        self.on_size_change = self._handle_resize

    def _build_view(self) -> None:
        header = build_page_header(title="ของฉัน", subtitle="ดูของที่อยู่กับคุณ กำหนดคืน และรายการย้อนหลัง", icon=ft.Icons.PERSON_OUTLINE)
        self.content = ft.Column(controls=[header, self.search_field, self.feedback, self.loan_container], spacing=16, expand=True, scroll=ft.ScrollMode.AUTO)
        self._render()

    def _render(self) -> None:
        borrower_id = self.current_user.borrower_id if self.current_user is not None else None
        if borrower_id is None:
            self.loan_container.content = build_state_view(
                "บัญชียังไม่ผูกกับข้อมูลผู้ยืม",
                "ให้เจ้าหน้าที่ผูกบัญชีนี้กับข้อมูลผู้ยืมในหน้า คนในระบบ หรือเข้าสู่ระบบด้วย LINE อีกครั้งหลังผูกบัญชี",
                icon=ft.Icons.LINK_OFF,
            )
            return
        loans = self.service.list_loans_for_borrower(borrower_id)
        query = (self.search_field.value or "").strip().casefold()
        if query:
            loans = [
                loan
                for loan in loans
                if query in loan.id.casefold()
                or any(query in _unit_label(self.service, unit_id).casefold() for unit_id in loan.unit_ids)
            ]
        loans.sort(key=lambda loan: (0 if _outstanding_units(loan) else 1, loan.due_date))
        if not loans:
            self.loan_container.content = build_state_view("ยังไม่มีรายการยืม", "เมื่อมีการยืม รายการจะแสดงที่นี่", icon=ft.Icons.ASSIGNMENT_OUTLINED)
            return
        cards = []
        for loan in loans:
            state = _loan_state(loan)
            items = loan.unit_ids if loan.status == "closed" else _outstanding_units(loan)
            cards.append(
                build_data_card(
                    title=loan.id,
                    icon=ft.Icons.RECEIPT_LONG_OUTLINED,
                    status=(state, _loan_state_label(state)),
                    fields=[
                        ("ครบกำหนด", loan.due_date),
                        ("ค้างอยู่", f"{len(_outstanding_units(loan))} / {len(loan.unit_ids)} ชิ้น"),
                        ("อุปกรณ์", ", ".join(_unit_label(self.service, unit_id) for unit_id in items)),
                        ("หมายเหตุ", loan.purpose or "-")
                    ],
                    full_width_fields=["อุปกรณ์", "หมายเหตุ"],
                )
            )
        self.loan_container.content = build_card_list(cards)

    def _handle_search(self, e: ft.ControlEvent | None) -> None:
        self._render()
        update_control(self)

    def _handle_resize(self, e: ft.LayoutSizeChangeEvent) -> None:
        handle_mobile_resize(self, self._build_view, e)


class HistoryWorkspaceView(LegacyHistoryView):
    """Readable audit stream with one search box and one event filter."""

    def __init__(self, service: FakeInventoryService | None = None, *, mobile: bool = False) -> None:
        ft.Container.__init__(self, expand=True, padding=0)
        self.service = service or FakeInventoryService()
        self.mobile = mobile
        self.search_field = ft.TextField(label="ค้นหาประวัติ", hint_text="ชื่อผู้ยืม รหัสอุปกรณ์ หรือรายละเอียด", prefix_icon=ft.Icons.SEARCH, height=52, on_change=self._handle_search)
        self.event_filter = ft.Dropdown(label="ประเภท", value="all", height=52, options=[ft.dropdown.Option("all", "ทุกเหตุการณ์"), ft.dropdown.Option("borrowed", "ยืม"), ft.dropdown.Option("available", "คืนพร้อมใช้"), ft.dropdown.Option("maintenance", "ส่งซ่อม"), ft.dropdown.Option("reported_lost", "แจ้งหาย"), ft.dropdown.Option("retired", "ปลดระวาง")], on_select=self._handle_search)
        self.history_container = ft.Container(expand=True)
        self._build_view()
        self.on_size_change = self._handle_resize

    def _build_view(self) -> None:
        header = build_page_header(title="ประวัติ", subtitle="ทุกการยืม คืน เปลี่ยนสถานะ และแก้ไขข้อมูลจะตามกลับได้", icon=ft.Icons.HISTORY)
        self.content = ft.Column(controls=[header, build_filter_bar(search_control=self.search_field, action_controls=[self.event_filter, ft.OutlinedButton("รีเฟรช", icon=ft.Icons.REFRESH, height=52, on_click=lambda e: self._clear())]), self.history_container], spacing=16, expand=True, scroll=ft.ScrollMode.AUTO)
        self._render()

    def _render(self) -> None:
        query = (self.search_field.value or "").strip()
        events = self.service.list_history()
        if query:
            keyword = query.casefold()
            events = [
                event
                for event in events
                if any(
                    keyword in str(value or "").casefold()
                    for value in (
                        event.description,
                        event.borrower_code,
                        event.staff_code,
                        event.equipment_name,
                        event.asset_code,
                    )
                )
            ]
        kind = self.event_filter.value or "all"
        if kind != "all":
            events = [event for event in events if event.event_type == kind]
        if not events:
            self.history_container.content = build_state_view("ไม่พบประวัติ", "ลองค้นหาด้วยชื่อหรือรหัสอุปกรณ์อื่น", icon=ft.Icons.HISTORY_TOGGLE_OFF)
            return
        cards = [
            build_data_card(
                title=event.description,
                icon=ft.Icons.HISTORY,
                status=(event.event_type, self._event_label(event.event_type)),
                fields=[("วันที่", event.event_date), ("ผู้ยืม", event.borrower_code or "-"), ("ผู้บันทึก", event.staff_code or "-"), ("อุปกรณ์", event.asset_code or event.equipment_name or "-")],
            )
            for event in events
        ]
        self.history_container.content = build_card_list(cards)

    def _clear(self) -> None:
        self.search_field.value = ""
        self.event_filter.value = "all"
        self._render()
        update_control(self)

    def _handle_search(self, e: ft.ControlEvent | None) -> None:
        self._render()
        update_control(self)

    @staticmethod
    def _event_label(value: str) -> str:
        return {"borrowed": "ยืมอุปกรณ์", "available": "คืนพร้อมใช้", "maintenance": "ส่งซ่อม", "reported_lost": "แจ้งหาย", "retired": "ปลดระวาง", "relocate": "ย้ายจุดเก็บ", "repair_complete": "ซ่อมเสร็จ"}.get(value, value)

    def _handle_resize(self, e: ft.LayoutSizeChangeEvent) -> None:
        handle_mobile_resize(self, self._build_view, e)
