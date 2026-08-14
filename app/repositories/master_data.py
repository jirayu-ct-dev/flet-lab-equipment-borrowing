from __future__ import annotations

import sqlite3
from datetime import date, datetime
from decimal import Decimal

from app.contracts import (
    Borrower,
    BorrowerFilter,
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
    Staff,
    StaffFilter,
    UnitFilter,
    UnitStatus,
    UpdateBorrower,
    UpdateEquipment,
    UpdateLocation,
    UpdateStaff,
)


def _decimal(value: object | None) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def _database_decimal(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _location(row: sqlite3.Row) -> Location:
    return Location(
        id=row["id"],
        location_code=row["location_code"],
        building=row["building"],
        room=row["room"],
        cabinet=row["cabinet"],
        shelf=row["shelf"],
        status=RecordStatus(row["status"]),
    )


def _equipment(row: sqlite3.Row) -> Equipment:
    return Equipment(
        id=row["id"],
        equipment_code=row["equipment_code"],
        name=row["name"],
        category=row["category"],
        manufacturer=row["manufacturer"],
        model=row["model"],
        default_location_id=row["default_location_id"],
        purchase_price=_decimal(row["purchase_price"]),
        status=RecordStatus(row["status"]),
        description=row["description"],
        created_at=_timestamp(row["created_at"]),
        updated_at=_timestamp(row["updated_at"]),
    )


def _unit(row: sqlite3.Row) -> EquipmentUnit:
    return EquipmentUnit(
        id=row["id"],
        asset_code=row["asset_code"],
        equipment_id=row["equipment_id"],
        serial_number=row["serial_number"],
        current_location_id=row["current_location_id"],
        status=UnitStatus(row["status"]),
        acquired_at=date.fromisoformat(row["acquired_at"]),
        purchase_price=_decimal(row["purchase_price"]),
        note=row["note"],
        created_at=_timestamp(row["created_at"]),
        updated_at=_timestamp(row["updated_at"]),
    )


def _staff(row: sqlite3.Row) -> Staff:
    return Staff(
        id=row["id"],
        staff_code=row["staff_code"],
        full_name=row["full_name"],
        email=row["email"],
        phone=row["phone"],
        status=RecordStatus(row["status"]),
        created_at=_timestamp(row["created_at"]),
        updated_at=_timestamp(row["updated_at"]),
    )


def _borrower(row: sqlite3.Row) -> Borrower:
    return Borrower(
        id=row["id"],
        borrower_code=row["borrower_code"],
        full_name=row["full_name"],
        department=row["department"],
        email=row["email"],
        phone=row["phone"],
        note=row["note"],
        status=RecordStatus(row["status"]),
        created_at=_timestamp(row["created_at"]),
        updated_at=_timestamp(row["updated_at"]),
    )


class MasterDataRepository:
    """SQL persistence for master data using a caller-owned connection."""

    def __init__(self, database: sqlite3.Connection) -> None:
        self.database = database

    def create_location(self, command: CreateLocation) -> Location:
        cursor = self.database.execute(
            """
            INSERT INTO locations(location_code, building, room, cabinet, shelf)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                command.location_code,
                command.building,
                command.room,
                command.cabinet,
                command.shelf,
            ),
        )
        return self.get_location(cursor.lastrowid)

    def get_location(self, location_id: int) -> Location | None:
        row = self.database.execute(
            "SELECT * FROM locations WHERE id = ?", (location_id,)
        ).fetchone()
        return _location(row) if row else None

    def update_location(self, location_id: int, command: UpdateLocation) -> Location | None:
        cursor = self.database.execute(
            """
            UPDATE locations
            SET building = ?, room = ?, cabinet = ?, shelf = ?, status = ?
            WHERE id = ?
            """,
            (
                command.building,
                command.room,
                command.cabinet,
                command.shelf,
                command.status.value,
                location_id,
            ),
        )
        return self.get_location(location_id) if cursor.rowcount else None

    def search_locations(self, filters: LocationFilter) -> list[Location]:
        clauses: list[str] = []
        values: list[object] = []
        if filters.query:
            clauses.append(
                "(location_code LIKE ? OR building LIKE ? OR room LIKE ? OR cabinet LIKE ? OR shelf LIKE ?)"
            )
            pattern = f"%{filters.query}%"
            values.extend([pattern] * 5)
        if filters.status:
            clauses.append("status = ?")
            values.append(filters.status.value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.database.execute(
            f"SELECT * FROM locations{where} ORDER BY location_code", values
        ).fetchall()
        return [_location(row) for row in rows]

    def create_equipment(self, command: CreateEquipment) -> Equipment:
        cursor = self.database.execute(
            """
            INSERT INTO equipment(
                equipment_code, name, category, manufacturer, model,
                default_location_id, purchase_price, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                command.equipment_code,
                command.name,
                command.category,
                command.manufacturer,
                command.model,
                command.default_location_id,
                _database_decimal(command.purchase_price),
                command.description,
            ),
        )
        return self.get_equipment(cursor.lastrowid)

    def get_equipment(self, equipment_id: int) -> Equipment | None:
        row = self.database.execute(
            "SELECT * FROM equipment WHERE id = ?", (equipment_id,)
        ).fetchone()
        return _equipment(row) if row else None

    def update_equipment(
        self, equipment_id: int, command: UpdateEquipment
    ) -> Equipment | None:
        cursor = self.database.execute(
            """
            UPDATE equipment SET
                name = ?, category = ?, manufacturer = ?, model = ?,
                default_location_id = ?, purchase_price = ?, status = ?,
                description = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ?
            """,
            (
                command.name,
                command.category,
                command.manufacturer,
                command.model,
                command.default_location_id,
                _database_decimal(command.purchase_price),
                command.status.value,
                command.description,
                equipment_id,
            ),
        )
        return self.get_equipment(equipment_id) if cursor.rowcount else None

    def search_equipment(self, filters: EquipmentFilter) -> list[Equipment]:
        clauses: list[str] = []
        values: list[object] = []
        if filters.query:
            clauses.append(
                "(equipment_code LIKE ? OR name LIKE ? OR category LIKE ? OR manufacturer LIKE ? OR model LIKE ?)"
            )
            pattern = f"%{filters.query}%"
            values.extend([pattern] * 5)
        if filters.status:
            clauses.append("status = ?")
            values.append(filters.status.value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.database.execute(
            f"SELECT * FROM equipment{where} ORDER BY equipment_code", values
        ).fetchall()
        return [_equipment(row) for row in rows]

    def create_staff(self, command: CreateStaff) -> Staff:
        cursor = self.database.execute(
            """
            INSERT INTO staff(staff_code, full_name, email, phone)
            VALUES (?, ?, ?, ?)
            """,
            (command.staff_code, command.full_name, command.email, command.phone),
        )
        return self.get_staff(cursor.lastrowid)

    def get_staff(self, staff_id: int) -> Staff | None:
        row = self.database.execute(
            "SELECT * FROM staff WHERE id = ?", (staff_id,)
        ).fetchone()
        return _staff(row) if row else None

    def update_staff(self, staff_id: int, command: UpdateStaff) -> Staff | None:
        cursor = self.database.execute(
            """
            UPDATE staff SET full_name = ?, email = ?, phone = ?, status = ?,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ?
            """,
            (command.full_name, command.email, command.phone, command.status.value, staff_id),
        )
        return self.get_staff(staff_id) if cursor.rowcount else None

    def search_staff(self, filters: StaffFilter) -> list[Staff]:
        clauses: list[str] = []
        values: list[object] = []
        if filters.query:
            clauses.append("(staff_code LIKE ? OR full_name LIKE ?)")
            pattern = f"%{filters.query}%"
            values.extend([pattern, pattern])
        if filters.status:
            clauses.append("status = ?")
            values.append(filters.status.value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.database.execute(
            f"SELECT * FROM staff{where} ORDER BY staff_code", values
        ).fetchall()
        return [_staff(row) for row in rows]

    def create_borrower(self, command: CreateBorrower) -> Borrower:
        cursor = self.database.execute(
            """
            INSERT INTO borrowers(
                borrower_code, full_name, department, email, phone, note
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                command.borrower_code,
                command.full_name,
                command.department,
                command.email,
                command.phone,
                command.note,
            ),
        )
        return self.get_borrower(cursor.lastrowid)

    def get_borrower(self, borrower_id: int) -> Borrower | None:
        row = self.database.execute(
            "SELECT * FROM borrowers WHERE id = ?", (borrower_id,)
        ).fetchone()
        return _borrower(row) if row else None

    def update_borrower(
        self, borrower_id: int, command: UpdateBorrower
    ) -> Borrower | None:
        cursor = self.database.execute(
            """
            UPDATE borrowers SET
                full_name = ?, department = ?, email = ?, phone = ?, note = ?,
                status = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ?
            """,
            (
                command.full_name,
                command.department,
                command.email,
                command.phone,
                command.note,
                command.status.value,
                borrower_id,
            ),
        )
        return self.get_borrower(borrower_id) if cursor.rowcount else None

    def search_borrowers(self, filters: BorrowerFilter) -> list[Borrower]:
        clauses: list[str] = []
        values: list[object] = []
        if filters.query:
            clauses.append("(borrower_code LIKE ? OR full_name LIKE ?)")
            pattern = f"%{filters.query}%"
            values.extend([pattern, pattern])
        if filters.status:
            clauses.append("status = ?")
            values.append(filters.status.value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.database.execute(
            f"SELECT * FROM borrowers{where} ORDER BY borrower_code", values
        ).fetchall()
        return [_borrower(row) for row in rows]

    def create_unit(
        self,
        *,
        asset_code: str,
        equipment_id: int,
        serial_number: str | None,
        location_id: int,
        acquired_at: date,
        purchase_price: Decimal | None,
        note: str | None,
    ) -> EquipmentUnit:
        cursor = self.database.execute(
            """
            INSERT INTO equipment_units(
                asset_code, equipment_id, serial_number, current_location_id,
                acquired_at, purchase_price, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                asset_code,
                equipment_id,
                serial_number,
                location_id,
                acquired_at.isoformat(),
                _database_decimal(purchase_price),
                note,
            ),
        )
        return self.get_unit(cursor.lastrowid)

    def get_unit(self, unit_id: int) -> EquipmentUnit | None:
        row = self.database.execute(
            "SELECT * FROM equipment_units WHERE id = ?", (unit_id,)
        ).fetchone()
        return _unit(row) if row else None

    def update_unit_note(self, unit_id: int, note: str | None) -> EquipmentUnit | None:
        cursor = self.database.execute(
            """
            UPDATE equipment_units SET note = ?,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ?
            """,
            (note, unit_id),
        )
        return self.get_unit(unit_id) if cursor.rowcount else None

    def transition_unit(
        self, unit_id: int, status: UnitStatus, location_id: int | None
    ) -> EquipmentUnit:
        self.database.execute(
            """
            UPDATE equipment_units SET status = ?, current_location_id = ?,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ?
            """,
            (status.value, location_id, unit_id),
        )
        unit = self.get_unit(unit_id)
        assert unit is not None
        return unit

    def add_adjustment(
        self, unit_id: int, action: str, reason: str, staff_id: int
    ) -> None:
        self.database.execute(
            """
            INSERT INTO inventory_adjustments(
                equipment_unit_id, action, reason, staff_id
            ) VALUES (?, ?, ?, ?)
            """,
            (unit_id, action, reason, staff_id),
        )

    def search_units(self, filters: UnitFilter) -> list[EquipmentUnit]:
        clauses: list[str] = []
        values: list[object] = []
        if filters.query:
            clauses.append(
                "(eu.asset_code LIKE ? OR eu.serial_number LIKE ? "
                "OR e.name LIKE ? OR e.category LIKE ? "
                "OR e.model LIKE ? OR e.manufacturer LIKE ?)"
            )
            pattern = f"%{filters.query}%"
            values.extend([pattern, pattern, pattern, pattern, pattern, pattern])
        if filters.equipment_id is not None:
            clauses.append("eu.equipment_id = ?")
            values.append(filters.equipment_id)
        if filters.location_id is not None:
            clauses.append("eu.current_location_id = ?")
            values.append(filters.location_id)
        if filters.status:
            clauses.append("eu.status = ?")
            values.append(filters.status.value)
        if filters.category:
            clauses.append("e.category = ?")
            values.append(filters.category)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.database.execute(
            f"SELECT eu.* FROM equipment_units AS eu "
            f"JOIN equipment AS e ON e.id = eu.equipment_id{where} "
            f"ORDER BY eu.asset_code",
            values,
        ).fetchall()
        return [_unit(row) for row in rows]
