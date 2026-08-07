from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from app.contracts import (
    EquipmentUnit,
    LostCase,
    LostResolution,
    RecordStatus,
    ResolveLostCase,
    ReturnOutcome,
    UnitStatus,
)
from app.database import connection, utc_now
from app.errors import (
    DuplicateCodeError,
    InactiveRecordError,
    InvalidTransitionError,
    LostCaseAlreadyResolved,
    NotFoundError,
    ValidationError,
)
from app.repositories import LostCaseRepository, MasterDataRepository, ReturnRepository


class SQLiteLostCaseService:
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
    ) -> Iterator[tuple[LostCaseRepository, MasterDataRepository, ReturnRepository]]:
        with connection(self.database_path) as database:
            database.execute("BEGIN IMMEDIATE")
            try:
                yield (
                    LostCaseRepository(database),
                    MasterDataRepository(database),
                    ReturnRepository(database),
                )
                database.commit()
            except Exception:
                database.rollback()
                raise

    def get(self, case_id: int) -> LostCase:
        with connection(self.database_path) as database:
            lost_case = LostCaseRepository(database).get(case_id)
        if lost_case is None:
            raise NotFoundError("lost_case", case_id)
        return lost_case

    def resolve_lost_case(
        self, case_id: int, command: ResolveLostCase
    ) -> LostCase:
        assessed_value = self._required_amount(
            command.assessed_value, "assessed_value"
        )
        approved_compensation = self._required_amount(
            command.approved_compensation, "approved_compensation"
        )
        if command.approved_by_staff_id is None:
            raise ValidationError(
                "approved_by_staff_id is required", field="approved_by_staff_id"
            )
        reason = command.reason.strip()
        if not reason:
            raise ValidationError("reason is required", field="reason")
        resolved_at = self._utc_timestamp(self.clock())

        try:
            with self._write() as (lost_cases, master_data, returns):
                lost_case = lost_cases.get(case_id)
                if lost_case is None:
                    raise NotFoundError("lost_case", case_id)
                if lost_case.resolution is not None:
                    raise LostCaseAlreadyResolved(
                        case_id, lost_case.resolution.value
                    )
                approver = master_data.get_staff(command.approved_by_staff_id)
                if approver is None:
                    raise NotFoundError("staff", command.approved_by_staff_id)
                if approver.status is not RecordStatus.ACTIVE:
                    raise InactiveRecordError("staff", approver.id)

                original_unit = master_data.get_unit(lost_case.equipment_unit_id)
                if original_unit is None:
                    raise NotFoundError(
                        "equipment_unit", lost_case.equipment_unit_id
                    )
                if original_unit.status is not UnitStatus.REPORTED_LOST:
                    raise InvalidTransitionError(
                        original_unit.status.value, command.resolution.value
                    )

                replacement_unit = self._apply_resolution(
                    master_data,
                    original_unit,
                    command,
                    approver.id,
                    reason,
                )
                replacement_unit_id = (
                    replacement_unit.id if replacement_unit is not None else None
                )
                before_json = self._case_json(lost_case)
                if not lost_cases.resolve(
                    case_id,
                    assessed_value=assessed_value,
                    approved_compensation=approved_compensation,
                    resolution=command.resolution,
                    approved_by_staff_id=approver.id,
                    resolved_at=resolved_at,
                    replacement_unit_id=replacement_unit_id,
                    note=command.note,
                ):
                    raise LostCaseAlreadyResolved(case_id, "unknown")
                resolved_case = lost_cases.get(case_id)
                assert resolved_case is not None
                lost_cases.add_audit_log(
                    case_id,
                    before_json=before_json,
                    after_json=self._case_json(resolved_case),
                    reason=reason,
                    staff_id=approver.id,
                    created_at=resolved_at,
                )

                loan_id = lost_cases.loan_id_for_case(case_id)
                assert loan_id is not None
                if returns.unresolved_item_count(loan_id) == 0:
                    returns.complete_loan(loan_id)
                return resolved_case
        except sqlite3.IntegrityError as error:
            message = str(error)
            replacement = command.replacement
            if replacement is not None and ".asset_code" in message:
                raise DuplicateCodeError(
                    "asset_code", replacement.asset_code
                ) from error
            if (
                replacement is not None
                and replacement.serial_number is not None
                and ".serial_number" in message
            ):
                raise DuplicateCodeError(
                    "serial_number", replacement.serial_number
                ) from error
            raise

    def _apply_resolution(
        self,
        repository: MasterDataRepository,
        original_unit: EquipmentUnit,
        command: ResolveLostCase,
        approver_id: int,
        reason: str,
    ) -> EquipmentUnit | None:
        if command.resolution is LostResolution.RECOVERED:
            if command.recovered_outcome not in {
                ReturnOutcome.AVAILABLE,
                ReturnOutcome.MAINTENANCE,
            }:
                raise ValidationError(
                    "recovered_outcome must be available or maintenance",
                    field="recovered_outcome",
                )
            if command.location_id is None:
                raise ValidationError(
                    "location_id is required for recovery", field="location_id"
                )
            if command.replacement is not None:
                raise ValidationError(
                    "replacement is only valid for replaced resolution",
                    field="replacement",
                )
            self._require_active_location(repository, command.location_id)
            repository.transition_unit(
                original_unit.id,
                UnitStatus(command.recovered_outcome.value),
                command.location_id,
            )
            return None

        if command.recovered_outcome is not None or command.location_id is not None:
            raise ValidationError(
                "recovery fields are only valid for recovered resolution",
                field="recovered_outcome",
            )

        if command.resolution is LostResolution.REPLACED:
            replacement = command.replacement
            if replacement is None:
                raise ValidationError(
                    "replacement is required for replaced resolution",
                    field="replacement",
                )
            asset_code = replacement.asset_code.strip()
            if not asset_code:
                raise ValidationError("asset_code is required", field="asset_code")
            if (
                replacement.serial_number is not None
                and not replacement.serial_number.strip()
            ):
                raise ValidationError(
                    "serial_number must not be blank", field="serial_number"
                )
            if replacement.purchase_price is not None and replacement.purchase_price < 0:
                raise ValidationError(
                    "purchase_price must not be negative", field="purchase_price"
                )
            self._require_active_location(repository, replacement.location_id)
            new_unit = repository.create_unit(
                asset_code=replacement.asset_code,
                equipment_id=original_unit.equipment_id,
                serial_number=replacement.serial_number,
                location_id=replacement.location_id,
                acquired_at=replacement.acquired_at,
                purchase_price=replacement.purchase_price,
                note=replacement.note,
            )
            repository.add_adjustment(
                new_unit.id, "acquire", reason, approver_id
            )
            repository.transition_unit(
                original_unit.id, UnitStatus.RETIRED, original_unit.current_location_id
            )
            return new_unit

        if command.replacement is not None:
            raise ValidationError(
                "replacement is only valid for replaced resolution",
                field="replacement",
            )
        repository.transition_unit(
            original_unit.id, UnitStatus.RETIRED, original_unit.current_location_id
        )
        return None

    @staticmethod
    def _required_amount(value: Decimal | None, field: str) -> Decimal:
        if value is None:
            raise ValidationError(f"{field} is required", field=field)
        if value < 0:
            raise ValidationError(f"{field} must not be negative", field=field)
        return value

    @staticmethod
    def _require_active_location(
        repository: MasterDataRepository, location_id: int
    ) -> None:
        location = repository.get_location(location_id)
        if location is None:
            raise NotFoundError("location", location_id)
        if location.status is not RecordStatus.ACTIVE:
            raise InactiveRecordError("location", location_id)

    @staticmethod
    def _utc_timestamp(value: datetime) -> str:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError("clock must return an aware datetime")
        return (
            value.astimezone(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )

    @staticmethod
    def _case_json(lost_case: LostCase) -> str:
        return json.dumps(
            {
                "assessed_value": (
                    str(lost_case.assessed_value)
                    if lost_case.assessed_value is not None
                    else None
                ),
                "approved_compensation": (
                    str(lost_case.approved_compensation)
                    if lost_case.approved_compensation is not None
                    else None
                ),
                "resolution": (
                    lost_case.resolution.value if lost_case.resolution else None
                ),
                "approved_by_staff_id": lost_case.approved_by_staff_id,
                "resolved_at": (
                    lost_case.resolved_at.isoformat()
                    if lost_case.resolved_at
                    else None
                ),
                "replacement_unit_id": lost_case.replacement_unit_id,
                "note": lost_case.note,
            },
            sort_keys=True,
        )
