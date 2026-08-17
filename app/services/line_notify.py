from __future__ import annotations

from datetime import date
from pathlib import Path

from app.contracts import LoanQueryState, LoanStatus
from app.database import bangkok_today, get_database_path
from app.repositories import auth_repository
from app.services.line_messaging import LineMessagingService
from app.services.queries import SQLiteLoanQueryService

REMINDER_STATES = (
    LoanQueryState.DUE_TODAY,
    LoanQueryState.DUE_SOON,
    LoanQueryState.OVERDUE,
)


class LineNotificationService:
    """LINE push notifications for loan events — always best-effort, never raises.

    Only users who logged in with LINE (have a line_sub) receive messages.
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
        messaging: LineMessagingService | None = None,
    ) -> None:
        self.database_path = database_path or get_database_path()
        self.messaging = messaging or LineMessagingService()
        self._notified_loan_ids: set[int] = set()

    def is_configured(self) -> bool:
        return self.messaging.is_configured()

    def _line_sub_for(self, borrower_code: str) -> str | None:
        try:
            return auth_repository.find_line_sub_by_borrower_code(
                self.database_path, borrower_code
            )
        except Exception:
            return None

    def _send(self, line_sub: str | None, text: str) -> None:
        if not self.is_configured() or not line_sub or not text:
            return
        try:
            self.messaging.send_text(line_sub, text)
        except Exception:
            return

    def notify_loan_created(
        self,
        *,
        borrower_code: str,
        transaction_code: str,
        due_date: str,
        unit_count: int,
    ) -> None:
        line_sub = self._line_sub_for(borrower_code)
        if not line_sub:
            return
        self._send(
            line_sub,
            (
                "แจ้งเตือน: บันทึกการยืมเรียบร้อย\n"
                f"• รหัสรายการ: {transaction_code}\n"
                f"• จำนวนอุปกรณ์: {unit_count} ชิ้น\n"
                f"• กำหนดคืน: {due_date}"
            ),
        )

    def notify_loan_returned(
        self,
        *,
        borrower_code: str,
        transaction_code: str,
        returned_count: int,
    ) -> None:
        line_sub = self._line_sub_for(borrower_code)
        if not line_sub:
            return
        self._send(
            line_sub,
            (
                "แจ้งเตือน: บันทึกการคืนเรียบร้อย\n"
                f"• รหัสรายการ: {transaction_code}\n"
                f"• คืนแล้ว: {returned_count} ชิ้น"
            ),
        )

    def send_due_reminders(self, today: date | None = None) -> int:
        """แจ้งเตือนรายการที่ครบกำหนด/ใกล้ครบกำหนด/เกินกำหนด คืน (รายการละครั้ง).

        Returns the number of messages sent. Never raises.
        """
        if not self.is_configured():
            return 0
        today = today or bangkok_today()
        service = SQLiteLoanQueryService(self.database_path)
        sent = 0
        try:
            summaries = service.search()
        except Exception:
            return 0
        for summary in summaries:
            if summary.status is not LoanStatus.ACTIVE:
                continue
            state = next(
                (state for state in REMINDER_STATES if state in summary.states),
                None,
            )
            if state is None or summary.id in self._notified_loan_ids:
                continue
            line_sub = self._line_sub_for(summary.borrower_code)
            if not line_sub:
                continue
            label = {
                LoanQueryState.DUE_TODAY: "ครบกำหนดคืนวันนี้",
                LoanQueryState.DUE_SOON: "ใกล้ถึงกำหนดคืน",
                LoanQueryState.OVERDUE: "เกินกำหนดคืนแล้ว",
            }[state]
            self._send(
                line_sub,
                (
                    "แจ้งเตือน: รายการยืม"
                    f" {label}\n"
                    f"• รหัสรายการ: {summary.transaction_code}\n"
                    f"• กำหนดคืน: {summary.due_date}"
                ),
            )
            self._notified_loan_ids.add(summary.id)
            sent += 1
        return sent