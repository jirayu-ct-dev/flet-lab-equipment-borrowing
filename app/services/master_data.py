from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Iterator

from app.contracts import (
    AcquireUnit,
    Borrower,
    BorrowerFilter,
    CompleteRepair,
    CreateBorrower,
    CreateEquipment,
    CreateLocation,
    CreateStaff,
    Equipment,
    EquipmentFilter,
    EquipmentUnit,
    Location,
    LocationFilter,
    RecordStatus,
    RelocateUnit,
    RetireUnit,
    Staff,
    StaffFilter,
    UnitFilter,
    UnitStatus,
    UpdateBorrower,
    UpdateEquipment,
    UpdateLocation,
    UpdateStaff,
    UpdateUnitNote,
)
from app.database import connection
from app.errors import (
    DuplicateCodeError,
    InactiveRecordError,
    InvalidTransitionError,
    NotFoundError,
    ValidationError,
)
from app.repositories import MasterDataRepository


DatabasePath = str | Path


def _required(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field} is required", field=field)
    return normalized


def _nonnegative(value: Decimal | None, field: str) -> None:
    if value is not None and value < 0:
        raise ValidationError(f"{field} must not be negative", field=field)


def _translate_duplicate(error: sqlite3.IntegrityError, **values: str | None) -> None:
    message = str(error)
    for field, value in values.items():
        if value is not None and f".{field}" in message:
            raise DuplicateCodeError(field, value) from error
    raise error


class _SQLiteService:
    def __init__(self, database_path: DatabasePath) -> None:
        self.database_path = database_path

    @contextmanager
    def _read(self) -> Iterator[MasterDataRepository]:
        with connection(self.database_path) as database:
            yield MasterDataRepository(database)

    @contextmanager
    def _write(self) -> Iterator[MasterDataRepository]:
        with connection(self.database_path) as database:
            database.execute("BEGIN IMMEDIATE")
            try:
                yield MasterDataRepository(database)
                database.commit()
            except Exception:
                database.rollback()
                raise


def _active_location(repository: MasterDataRepository, location_id: int) -> Location:
    location = repository.get_location(location_id)
    if location is None:
        raise NotFoundError("location", location_id)
    if location.status is not RecordStatus.ACTIVE:
        raise InactiveRecordError("location", location_id)
    return location


def _active_equipment(repository: MasterDataRepository, equipment_id: int) -> Equipment:
    equipment = repository.get_equipment(equipment_id)
    if equipment is None:
        raise NotFoundError("equipment", equipment_id)
    if equipment.status is not RecordStatus.ACTIVE:
        raise InactiveRecordError("equipment", equipment_id)
    return equipment


def _active_staff(repository: MasterDataRepository, staff_id: int) -> Staff:
    staff = repository.get_staff(staff_id)
    if staff is None:
        raise NotFoundError("staff", staff_id)
    if staff.status is not RecordStatus.ACTIVE:
        raise InactiveRecordError("staff", staff_id)
    return staff


class SQLiteLocationService(_SQLiteService):
    def create(self, command: CreateLocation) -> Location:
        _required(command.location_code, "location_code")
        _required(command.room, "room")
        try:
            with self._write() as repository:
                return repository.create_location(command)
        except sqlite3.IntegrityError as error:
            _translate_duplicate(error, location_code=command.location_code)
            raise

    def get(self, location_id: int) -> Location:
        with self._read() as repository:
            location = repository.get_location(location_id)
        if location is None:
            raise NotFoundError("location", location_id)
        return location

    def update(self, location_id: int, command: UpdateLocation) -> Location:
        _required(command.room, "room")
        with self._write() as repository:
            location = repository.update_location(location_id, command)
            if location is None:
                raise NotFoundError("location", location_id)
            return location

    def search(self, filters: LocationFilter = LocationFilter()) -> list[Location]:
        with self._read() as repository:
            return repository.search_locations(filters)


class SQLiteEquipmentService(_SQLiteService):
    def create(self, command: CreateEquipment) -> Equipment:
        _required(command.equipment_code, "equipment_code")
        _required(command.name, "name")
        _nonnegative(command.purchase_price, "purchase_price")
        try:
            with self._write() as repository:
                if command.default_location_id is not None:
                    _active_location(repository, command.default_location_id)
                return repository.create_equipment(command)
        except sqlite3.IntegrityError as error:
            _translate_duplicate(error, equipment_code=command.equipment_code)
            raise

    def get(self, equipment_id: int) -> Equipment:
        with self._read() as repository:
            equipment = repository.get_equipment(equipment_id)
        if equipment is None:
            raise NotFoundError("equipment", equipment_id)
        return equipment

    def update(self, equipment_id: int, command: UpdateEquipment) -> Equipment:
        _required(command.name, "name")
        _nonnegative(command.purchase_price, "purchase_price")
        with self._write() as repository:
            if command.default_location_id is not None:
                _active_location(repository, command.default_location_id)
            equipment = repository.update_equipment(equipment_id, command)
            if equipment is None:
                raise NotFoundError("equipment", equipment_id)
            return equipment

    def search(self, filters: EquipmentFilter = EquipmentFilter()) -> list[Equipment]:
        with self._read() as repository:
            return repository.search_equipment(filters)


class SQLiteStaffService(_SQLiteService):
    def create(self, command: CreateStaff) -> Staff:
        _required(command.staff_code, "staff_code")
        _required(command.full_name, "full_name")
        try:
            with self._write() as repository:
                return repository.create_staff(command)
        except sqlite3.IntegrityError as error:
            _translate_duplicate(error, staff_code=command.staff_code)
            raise

    def get(self, staff_id: int) -> Staff:
        with self._read() as repository:
            staff = repository.get_staff(staff_id)
        if staff is None:
            raise NotFoundError("staff", staff_id)
        return staff

    def update(self, staff_id: int, command: UpdateStaff) -> Staff:
        _required(command.full_name, "full_name")
        with self._write() as repository:
            staff = repository.update_staff(staff_id, command)
            if staff is None:
                raise NotFoundError("staff", staff_id)
            return staff

    def search(self, filters: StaffFilter = StaffFilter()) -> list[Staff]:
        with self._read() as repository:
            return repository.search_staff(filters)


class SQLiteBorrowerService(_SQLiteService):
    def create(self, command: CreateBorrower) -> Borrower:
        _required(command.borrower_code, "borrower_code")
        _required(command.full_name, "full_name")
        try:
            with self._write() as repository:
                return repository.create_borrower(command)
        except sqlite3.IntegrityError as error:
            _translate_duplicate(error, borrower_code=command.borrower_code)
            raise

    def get(self, borrower_id: int) -> Borrower:
        with self._read() as repository:
            borrower = repository.get_borrower(borrower_id)
        if borrower is None:
            raise NotFoundError("borrower", borrower_id)
        return borrower

    def update(self, borrower_id: int, command: UpdateBorrower) -> Borrower:
        _required(command.full_name, "full_name")
        with self._write() as repository:
            borrower = repository.update_borrower(borrower_id, command)
            if borrower is None:
                raise NotFoundError("borrower", borrower_id)
            return borrower

    def search(self, filters: BorrowerFilter = BorrowerFilter()) -> list[Borrower]:
        with self._read() as repository:
            return repository.search_borrowers(filters)


class SQLiteUnitService(_SQLiteService):
    def acquire(self, command: AcquireUnit) -> EquipmentUnit:
        _required(command.asset_code, "asset_code")
        _required(command.reason, "reason")
        if command.serial_number is not None:
            _required(command.serial_number, "serial_number")
        _nonnegative(command.purchase_price, "purchase_price")
        try:
            with self._write() as repository:
                _active_equipment(repository, command.equipment_id)
                _active_location(repository, command.current_location_id)
                _active_staff(repository, command.recorded_by_staff_id)
                unit = repository.create_unit(
                    asset_code=command.asset_code,
                    equipment_id=command.equipment_id,
                    serial_number=command.serial_number,
                    location_id=command.current_location_id,
                    acquired_at=command.acquired_at,
                    purchase_price=command.purchase_price,
                    note=command.note,
                )
                repository.add_adjustment(
                    unit.id, "acquire", command.reason, command.recorded_by_staff_id
                )
                return unit
        except sqlite3.IntegrityError as error:
            _translate_duplicate(
                error,
                asset_code=command.asset_code,
                serial_number=command.serial_number,
            )
            raise

    def get(self, unit_id: int) -> EquipmentUnit:
        with self._read() as repository:
            unit = repository.get_unit(unit_id)
        if unit is None:
            raise NotFoundError("equipment_unit", unit_id)
        return unit

    def update_note(self, unit_id: int, command: UpdateUnitNote) -> EquipmentUnit:
        with self._write() as repository:
            unit = repository.update_unit_note(unit_id, command.note)
            if unit is None:
                raise NotFoundError("equipment_unit", unit_id)
            return unit

    def relocate(self, unit_id: int, command: RelocateUnit) -> EquipmentUnit:
        _required(command.reason, "reason")
        with self._write() as repository:
            unit = self._get_unit(repository, unit_id)
            if unit.status not in {UnitStatus.AVAILABLE, UnitStatus.MAINTENANCE}:
                raise InvalidTransitionError(unit.status.value, "relocated")
            _active_location(repository, command.location_id)
            _active_staff(repository, command.recorded_by_staff_id)
            unit = repository.transition_unit(unit_id, unit.status, command.location_id)
            repository.add_adjustment(
                unit_id, "relocate", command.reason, command.recorded_by_staff_id
            )
            return unit

    def retire(self, unit_id: int, command: RetireUnit) -> EquipmentUnit:
        _required(command.reason, "reason")
        with self._write() as repository:
            unit = self._get_unit(repository, unit_id)
            if unit.status not in {UnitStatus.AVAILABLE, UnitStatus.MAINTENANCE}:
                raise InvalidTransitionError(unit.status.value, UnitStatus.RETIRED.value)
            _active_staff(repository, command.recorded_by_staff_id)
            unit = repository.transition_unit(
                unit_id, UnitStatus.RETIRED, unit.current_location_id
            )
            repository.add_adjustment(
                unit_id, "retire", command.reason, command.recorded_by_staff_id
            )
            return unit

    def complete_repair(
        self, unit_id: int, command: CompleteRepair
    ) -> EquipmentUnit:
        _required(command.reason, "reason")
        with self._write() as repository:
            unit = self._get_unit(repository, unit_id)
            if unit.status is not UnitStatus.MAINTENANCE:
                raise InvalidTransitionError(unit.status.value, UnitStatus.AVAILABLE.value)
            _active_location(repository, command.location_id)
            _active_staff(repository, command.recorded_by_staff_id)
            unit = repository.transition_unit(
                unit_id, UnitStatus.AVAILABLE, command.location_id
            )
            repository.add_adjustment(
                unit_id,
                "repair_complete",
                command.reason,
                command.recorded_by_staff_id,
            )
            return unit

    def search(self, filters: UnitFilter = UnitFilter()) -> list[EquipmentUnit]:
        with self._read() as repository:
            return repository.search_units(filters)

    @staticmethod
    def _get_unit(repository: MasterDataRepository, unit_id: int) -> EquipmentUnit:
        unit = repository.get_unit(unit_id)
        if unit is None:
            raise NotFoundError("equipment_unit", unit_id)
        return unit
