from datetime import date

from app.contracts import LoanQueryState, LoanStatus, LoanSummary
from app.services import line_messaging, line_notify
from app.services.fake_services import FakeInventoryService
from app.services.line_messaging import LineMessagingService
from app.services.line_notify import LineNotificationService
from app.views.borrow_flow import BorrowFlowView
from app.views.loans import LoansView
from tests.test_auth_fixtures import admin_user


class _FakeResponse:
    def __init__(self, body: bytes = b"{}") -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _Recorder:
    def __init__(self) -> None:
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        return _FakeResponse()


class _StubMessaging:
    def __init__(self, *, configured: bool = True, error: Exception | None = None):
        self.configured = configured
        self.error = error
        self.sent: list[tuple[str, str]] = []

    def is_configured(self) -> bool:
        return self.configured

    def send_text(self, line_user_id: str, text: str) -> None:
        if self.error is not None:
            raise self.error
        self.sent.append((line_user_id, text))


def _summary(
    *,
    code: str,
    borrower_code: str,
    due_date: date,
    states=(),
    status=LoanStatus.ACTIVE,
) -> LoanSummary:
    return LoanSummary(
        id=hash(code),
        transaction_code=code,
        borrower_id=1,
        borrower_code=borrower_code,
        borrower_name="Tester",
        borrow_date=date(2026, 8, 1),
        due_date=due_date,
        status=status,
        item_count=1,
        resolved_item_count=0,
        outstanding_item_count=1,
        states=states,
    )


def test_send_text_posts_correct_request(monkeypatch) -> None:
    rec = _Recorder()
    monkeypatch.setattr(line_messaging, "urlopen", rec)
    monkeypatch.setenv("LINE_MESSAGING_CHANNEL_ACCESS_TOKEN", "token-1")
    service = LineMessagingService()

    service.send_text("u-1", "สวัสดี")

    (request,) = rec.requests
    import json

    assert request.full_url == "https://api.line.me/v2/bot/message/push"
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == "Bearer token-1"
    assert request.headers["Content-type"] == "application/json"
    assert json.loads(request.data) == {
        "to": "u-1",
        "messages": [{"type": "text", "text": "สวัสดี"}],
    }


def test_send_text_skips_when_unconfigured(monkeypatch) -> None:
    rec = _Recorder()
    monkeypatch.setattr(line_messaging, "urlopen", rec)
    service = LineMessagingService()

    service.send_text("u-1", "ข้อความ")

    assert rec.requests == []


def test_send_text_skips_empty_arguments(monkeypatch) -> None:
    rec = _Recorder()
    monkeypatch.setattr(line_messaging, "urlopen", rec)
    monkeypatch.setenv("LINE_MESSAGING_CHANNEL_ACCESS_TOKEN", "token-1")
    service = LineMessagingService()

    service.send_text("", "ข้อความ")
    service.send_text("u-1", "")

    assert rec.requests == []


def test_notify_loan_created_sends_when_line_sub_exists(monkeypatch) -> None:
    messaging = _StubMessaging()
    notifier = LineNotificationService(database_path=":memory:", messaging=messaging)
    monkeypatch.setattr(
        line_notify.auth_repository,
        "find_line_sub_by_borrower_code",
        lambda _db, code: "u-1" if code == "BR-001" else None,
    )

    notifier.notify_loan_created(
        borrower_code="BR-001",
        transaction_code="LOAN-1",
        due_date="2026-08-20",
        unit_count=2,
    )

    assert len(messaging.sent) == 1
    line_sub, text = messaging.sent[0]
    assert line_sub == "u-1"
    assert "บันทึกการยืมเรียบร้อย" in text
    assert "LOAN-1" in text
    assert "2026-08-20" in text


def test_notify_loan_created_skips_when_no_line_sub(monkeypatch) -> None:
    messaging = _StubMessaging()
    notifier = LineNotificationService(database_path=":memory:", messaging=messaging)
    monkeypatch.setattr(
        line_notify.auth_repository,
        "find_line_sub_by_borrower_code",
        lambda _db, code: None,
    )

    notifier.notify_loan_created(
        borrower_code="BR-001",
        transaction_code="LOAN-1",
        due_date="2026-08-20",
        unit_count=1,
    )

    assert messaging.sent == []


def test_notify_loan_returned_sends_when_line_sub_exists(monkeypatch) -> None:
    messaging = _StubMessaging()
    notifier = LineNotificationService(database_path=":memory:", messaging=messaging)
    monkeypatch.setattr(
        line_notify.auth_repository,
        "find_line_sub_by_borrower_code",
        lambda _db, code: "u-9",
    )

    notifier.notify_loan_returned(
        borrower_code="BR-001",
        transaction_code="LOAN-2",
        returned_count=1,
    )

    assert len(messaging.sent) == 1
    line_sub, text = messaging.sent[0]
    assert line_sub == "u-9"
    assert "บันทึกการคืนเรียบร้อย" in text
    assert "LOAN-2" in text


def test_notify_never_raises(monkeypatch) -> None:
    messaging = _StubMessaging(error=RuntimeError("LINE down"))
    notifier = LineNotificationService(database_path=":memory:", messaging=messaging)
    monkeypatch.setattr(
        line_notify.auth_repository,
        "find_line_sub_by_borrower_code",
        lambda _db, code: "u-1",
    )

    notifier.notify_loan_created(
        borrower_code="BR-001",
        transaction_code="LOAN-1",
        due_date="2026-08-20",
        unit_count=1,
    )

    assert messaging.sent == []


def test_send_due_reminders_sends_once_per_loan(monkeypatch) -> None:
    messaging = _StubMessaging()
    notifier = LineNotificationService(database_path=":memory:", messaging=messaging)
    monkeypatch.setattr(
        line_notify.auth_repository,
        "find_line_sub_by_borrower_code",
        lambda _db, code: "u-1",
    )
    summaries = [
        _summary(
            code="LOAN-TODAY",
            borrower_code="BR-001",
            due_date=date(2026, 8, 16),
            states=(LoanQueryState.DUE_TODAY,),
        ),
        _summary(
            code="LOAN-OVERDUE",
            borrower_code="BR-002",
            due_date=date(2026, 8, 15),
            states=(LoanQueryState.OVERDUE,),
        ),
        _summary(
            code="LOAN-FAR",
            borrower_code="BR-003",
            due_date=date(2026, 8, 30),
            states=(),
        ),
    ]
    monkeypatch.setattr(
        line_notify,
        "SQLiteLoanQueryService",
        lambda _path: _FakeQueryService(summaries),
    )

    first = notifier.send_due_reminders()
    second = notifier.send_due_reminders()

    assert first == 2
    assert second == 0
    assert {line_sub for line_sub, _ in messaging.sent} == {"u-1"}
    assert len(messaging.sent) == 2


def test_send_due_reminders_skips_completed_and_unlinked(monkeypatch) -> None:
    messaging = _StubMessaging()
    notifier = LineNotificationService(database_path=":memory:", messaging=messaging)
    monkeypatch.setattr(
        line_notify.auth_repository,
        "find_line_sub_by_borrower_code",
        lambda _db, code: "u-1" if code == "BR-001" else None,
    )
    summaries = [
        _summary(
            code="LOAN-DONE",
            borrower_code="BR-001",
            due_date=date(2026, 8, 16),
            states=(LoanQueryState.DUE_TODAY,),
            status=LoanStatus.COMPLETED,
        ),
        _summary(
            code="LOAN-NOLINK",
            borrower_code="BR-002",
            due_date=date(2026, 8, 15),
            states=(LoanQueryState.OVERDUE,),
        ),
    ]
    monkeypatch.setattr(
        line_notify,
        "SQLiteLoanQueryService",
        lambda _path: _FakeQueryService(summaries),
    )

    sent = notifier.send_due_reminders()

    assert sent == 0
    assert messaging.sent == []


def test_send_due_reminders_skips_when_unconfigured() -> None:
    messaging = _StubMessaging(configured=False)
    notifier = LineNotificationService(database_path=":memory:", messaging=messaging)

    sent = notifier.send_due_reminders()

    assert sent == 0


class _FakeQueryService:
    def __init__(self, summaries) -> None:
        self._summaries = summaries

    def search(self):
        return self._summaries


def _notifier_with_messaging(messaging=None):
    return LineNotificationService(
        database_path=":memory:", messaging=messaging or _StubMessaging()
    )


def test_borrow_view_notifies_after_borrow(monkeypatch) -> None:
    messaging = _StubMessaging()
    notifier = _notifier_with_messaging(messaging)
    monkeypatch.setattr(
        line_notify.auth_repository,
        "find_line_sub_by_borrower_code",
        lambda _db, code: "u-1" if code == "BR-001" else None,
    )
    view = BorrowFlowView(
        FakeInventoryService(),
        current_user=admin_user(),
        notifier=notifier,
    )
    view.borrower_dropdown.value = "BR-001"
    view.staff_dropdown.value = "ST-001"
    view.unit_dropdown.value = "unit-1"
    view.purpose.value = "ใช้ทดลอง"

    view._handle_borrow(None)

    assert len(messaging.sent) == 1
    text = messaging.sent[0][1]
    assert "บันทึกการยืมเรียบร้อย" in text


def test_loans_view_notifies_after_return(monkeypatch) -> None:
    service = FakeInventoryService()
    messaging = _StubMessaging()
    notifier = _notifier_with_messaging(messaging)
    monkeypatch.setattr(
        line_notify.auth_repository,
        "find_line_sub_by_borrower_code",
        lambda _db, code: "u-1" if code == "BR-001" else None,
    )
    view = LoansView(service, current_user=admin_user(), notifier=notifier)

    loan = service.get_loan("loan-1")
    view._open_return_dialog(None, loan)
    view._handle_confirm_return(None)

    assert len(messaging.sent) == 1
    text = messaging.sent[0][1]
    assert "บันทึกการคืนเรียบร้อย" in text