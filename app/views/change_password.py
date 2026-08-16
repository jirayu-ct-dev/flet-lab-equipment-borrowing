from __future__ import annotations

from typing import Callable

import flet as ft

from app.components.common import build_card, build_page_header, update_control
from app.contracts import AppUser, AuthService, ChangePasswordCommand
from app.errors import AuthenticationError, DomainError
from app.security import validate_password_strength
from app.theme import COLOR_TEXT_SECONDARY, CONTROL_RADIUS


class ChangePasswordView(ft.Container):
    """Self-service password change; calls on_done after a successful change."""

    def __init__(
        self,
        auth_service: AuthService,
        user: AppUser,
        *,
        on_done: Callable[[], None],
        on_cancel: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(expand=True, padding=0, alignment=ft.Alignment.CENTER)
        self.auth_service = auth_service
        self.user = user
        self.on_done = on_done
        self.on_cancel = on_cancel
        self.current_password_field = ft.TextField(
            label="รหัสผ่านปัจจุบัน",
            password=True,
            can_reveal_password=True,
            width=float("inf"),
            height=52,
            border_radius=CONTROL_RADIUS,
            on_submit=self._handle_submit,
        )
        self.new_password_field = ft.TextField(
            label="รหัสผ่านใหม่",
            password=True,
            can_reveal_password=True,
            width=float("inf"),
            height=52,
            border_radius=CONTROL_RADIUS,
            on_submit=self._handle_submit,
        )
        self.confirm_password_field = ft.TextField(
            label="ยืนยันรหัสผ่านใหม่",
            password=True,
            can_reveal_password=True,
            width=float("inf"),
            height=52,
            border_radius=CONTROL_RADIUS,
            on_submit=self._handle_submit,
        )
        self.feedback = ft.Text("", size=13)
        self.submit_button = ft.FilledButton(
            "บันทึกรหัสผ่านใหม่",
            height=52,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=CONTROL_RADIUS),
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
            ),
            on_click=self._handle_submit,
        )
        if on_cancel is not None:
            self.cancel_button = ft.OutlinedButton(
                "ยกเลิก",
                height=52,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=CONTROL_RADIUS),
                ),
                on_click=lambda e: on_cancel(),
            )
            self.submit_button.expand = True
            self.cancel_button.expand = True
            buttons: ft.Control = ft.Row(
                controls=[self.submit_button, self.cancel_button],
                spacing=12,
            )
        else:
            self.cancel_button = None
            self.submit_button.width = float("inf")
            buttons = self.submit_button
        self.content = build_card(
            content=ft.Column(
                controls=[
                    build_page_header(
                        title="เปลี่ยนรหัสผ่าน",
                        subtitle=f"บัญชี: {user.display_name}",
                        icon=ft.Icons.LOCK_RESET,
                    ),
                    self.current_password_field,
                    self.new_password_field,
                    self.confirm_password_field,
                    self.feedback,
                    buttons,
                ],
                spacing=14,
                tight=True,
            ),
            padding=32,
            width=420,
        )

    def _handle_submit(self, e: ft.ControlEvent | None) -> None:
        new_password = self.new_password_field.value or ""
        if new_password != (self.confirm_password_field.value or ""):
            self._set_feedback("รหัสผ่านใหม่ไม่ตรงกัน", error=True)
            update_control(self)
            return
        strength_error = validate_password_strength(new_password)
        if strength_error is not None:
            self._set_feedback(strength_error, error=True)
            update_control(self)
            return
        try:
            self.auth_service.change_password(
                self.user.id,
                ChangePasswordCommand(
                    current_password=self.current_password_field.value or "",
                    new_password=new_password,
                ),
            )
        except AuthenticationError:
            self._set_feedback("รหัสผ่านปัจจุบันไม่ถูกต้อง", error=True)
            update_control(self)
            return
        except DomainError as error:
            self._set_feedback(error.message, error=True)
            update_control(self)
            return
        self.on_done()

    def _set_feedback(self, message: str, *, error: bool) -> None:
        self.feedback.value = message
        self.feedback.color = ft.Colors.RED_700 if error else COLOR_TEXT_SECONDARY
