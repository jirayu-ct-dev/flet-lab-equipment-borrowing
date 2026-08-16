from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.contracts import (
    CreateLostReport,
    LostReport,
    LostReportStatus,
    RecordStatus,
    ReviewLostReport,
    UnitStatus,
)
from app.database import connection, utc_now
from app.errors import (
    InactiveRecordError,
    NotFoundError,
    ReportAlreadyReviewed,
    ValidationError,
)
from app.repositories import (
    LostReportRepository,
    MasterDataRepository,
    ReturnRepository,
)


class SQLiteLostReportService:
    def __init__(
        self,
        database_path: str | Path,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.database_path = database_path
        self.clock = clock

    @contextmanager
    def _write(
        self,
    ) -> Iterator[
        tuple[LostReportRepository, MasterDataRepository, ReturnRepository]
    ]:
        with connection(self.database_path) as database:
            database.execute("BEGIN IMMEDIATE")
            try:
                yield (
                    LostReportRepository(database),
                    MasterDataRepository(database),
                    ReturnRepository(database),
                )
                database.commit()
            except Exception:
                database.rollback()
                raise

    def create_report(self, command: CreateLostReport) -> LostReport:
        reported_at = self._utc_timestamp(self.clock())
        with self._write() as (lost_reports, master_data, _):
            borrower = master_data.get_borrower(command.borrower_id)
            if borrower is None:
                raise NotFoundError("borrower", command.borrower_id)
            if borrower.status is not RecordStatus.ACTIVE:
                raise InactiveRecordError("borrower", borrower.id)
            if master_data.get_unit(command.equipment_unit_id) is None:
                raise NotFoundError("equipment_unit", command.equipment_unit_id)
            return lost_reports.create(command, reported_at)

    def list_pending_reports(self) -> list[LostReport]:
        with connection(self.database_path) as database:
            return LostReportRepository(database).list_pending()

    def list_reports_for_borrower(self, borrower_id: int) -> list[LostReport]:
        with connection(self.database_path) as database:
            return LostReportRepository(database).list_for_borrower(borrower_id)

    def review_report(self, report_id: int, command: ReviewLostReport) -> LostReport:
        reviewed_at = self._utc_timestamp(self.clock())
        with self._write() as (lost_reports, master_data, returns):
            report = lost_reports.get(report_id)
            if report is None:
                raise NotFoundError("lost_report", report_id)
            if report.status is not LostReportStatus.PENDING:
                raise ReportAlreadyReviewed(report_id, report.status.value)
            approver = master_data.get_staff(command.reviewed_by_staff_id)
            if approver is None:
                raise NotFoundError("staff", command.reviewed_by_staff_id)
            if approver.status is not RecordStatus.ACTIVE:
                raise InactiveRecordError("staff", approver.id)

            if command.approved:
                unit = master_data.get_unit(report.equipment_unit_id)
                if unit is None:
                    raise NotFoundError("equipment_unit", report.equipment_unit_id)
                master_data.transition_unit(
                    unit.id, UnitStatus.REPORTED_LOST, None
                )
                borrow_item_id = lost_reports.open_borrow_item_id(unit.id)
                if borrow_item_id is not None:
                    returns.open_lost_case(
                        unit.id, borrow_item_id, reviewed_at, report.description
                    )

            if not lost_reports.review(
                report_id,
                status=(
                    LostReportStatus.APPROVED
                    if command.approved
                    else LostReportStatus.REJECTED
                ),
                reviewed_by_staff_id=approver.id,
                reviewed_at=reviewed_at,
                review_note=command.review_note,
            ):
                raise ReportAlreadyReviewed(report_id, report.status.value)
            reviewed = lost_reports.get(report_id)
            assert reviewed is not None
            return reviewed

    @staticmethod
    def _utc_timestamp(value: datetime) -> str:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError("clock must return an aware datetime")
        return (
            value.astimezone(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )
