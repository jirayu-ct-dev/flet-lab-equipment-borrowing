from __future__ import annotations

from typing import Callable

import flet as ft

from app.components.common import build_card, build_page_header, update_control
from app.contracts import AppUser, AuthService, LoginCommand
from app.errors import AuthenticationError, DomainError
from app.services.auth_service import INACTIVE_USER_MESSAGE
from app.theme import COLOR_BORDER, COLOR_TEXT_SECONDARY, CONTROL_RADIUS

LINE_BUTTON_GREEN = "#06C755"


class LoginView(ft.Container):
    """Email/password login form; calls on_success with the authenticated user."""

    def __init__(
        self,
        auth_service: AuthService,
        *,
        on_success: Callable[[AppUser], None],
        on_line_login: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(expand=True, padding=0, alignment=ft.Alignment.CENTER)
        self.auth_service = auth_service
        self.on_success = on_success
        self.on_line_login = on_line_login
        self.email_field = ft.TextField(
            label="อีเมล",
            prefix_icon=ft.Icons.MAIL,
            width=float("inf"),
            height=52,
            border_radius=CONTROL_RADIUS,
            on_submit=self._handle_login,
            autofocus=True,
        )
        self.password_field = ft.TextField(
            label="รหัสผ่าน",
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK,
            width=float("inf"),
            height=52,
            border_radius=CONTROL_RADIUS,
            on_submit=self._handle_login,
        )
        self.feedback = ft.Text("", size=13)
        self.login_button = ft.FilledButton(
            "เข้าสู่ระบบ",
            icon=ft.Icons.LOGIN,
            width=float("inf"),
            height=52,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=CONTROL_RADIUS),
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
            ),
            on_click=self._handle_login,
        )
        if on_line_login is not None:
            self.line_button = ft.FilledButton(
                content=ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Text(
                                "LINE",
                                size=8,
                                weight=ft.FontWeight.BOLD,
                                color=LINE_BUTTON_GREEN,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            bgcolor=ft.Colors.WHITE,
                            border_radius=6,
                            width=24,
                            height=24,
                            padding=2,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Text(
                            "ล็อกอินด้วย LINE",
                            size=14,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.WHITE,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                    tight=True,
                ),
                bgcolor=LINE_BUTTON_GREEN,
                width=float("inf"),
                height=52,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=CONTROL_RADIUS),
                ),
                on_click=lambda e: on_line_login(),
            )
        else:
            self.line_button = None
        card_controls: list[ft.Control] = [
            build_page_header(
                title="ยืม-คืนครุภัณฑ์ BRU-CS",
                subtitle="เข้าสู่ระบบเพื่อใช้งาน",
                icon=ft.Icons.INVENTORY_2_ROUNDED,
            ),
        ]
        if self.line_button is not None:
            card_controls.append(self.line_button)
            card_controls.append(
                ft.Row(
                    controls=[
                        ft.Container(expand=True, height=1, bgcolor=COLOR_BORDER),
                        ft.Text(
                            "หรือ",
                            size=13,
                            color=COLOR_TEXT_SECONDARY,
                        ),
                        ft.Container(expand=True, height=1, bgcolor=COLOR_BORDER),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=12,
                )
            )
        card_controls.extend(
            [
                self.email_field,
                self.password_field,
                self.feedback,
                self.login_button,
            ]
        )
        self.content = build_card(
            content=ft.Column(
                controls=card_controls,
                spacing=14,
                tight=True,
            ),
            padding=32,
            width=420,
        )

    def _handle_login(self, e: ft.ControlEvent | None) -> None:
        email = (self.email_field.value or "").strip().lower()
        password = self.password_field.value or ""
        if not email or not password:
            self._set_feedback("กรุณากรอกอีเมลและรหัสผ่าน", error=True)
            update_control(self)
            return
        try:
            user = self.auth_service.authenticate(
                LoginCommand(identity=email, password=password)
            )
        except AuthenticationError as error:
            if error.message == INACTIVE_USER_MESSAGE:
                self._set_feedback("บัญชีถูกปิดใช้งาน กรุณาติดต่อผู้ดูแลระบบ", error=True)
            else:
                self._set_feedback("อีเมลหรือรหัสผ่านไม่ถูกต้อง", error=True)
            update_control(self)
            return
        except DomainError as error:
            self._set_feedback(error.message, error=True)
            update_control(self)
            return
        self.on_success(user)

    def _set_feedback(self, message: str, *, error: bool) -> None:
        self.feedback.value = message
        self.feedback.color = ft.Colors.RED_700 if error else COLOR_TEXT_SECONDARY
