from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.contracts import (
    AcquireUnit,
    BorrowerFilter,
    CreateBorrower,
    CreateDraftLoan,
    CreateEquipment,
    CreateLocation,
    CreateStaff,
    EquipmentFilter,
    LostResolution,
    ReplacementUnit,
    RecordStatus,
    RecordReturn,
    RelocateUnit,
    ReturnItemCommand,
    ReturnOutcome,
    ResolveLostCase,
    RetireUnit,
    CompleteRepair,
    StaffFilter,
    UnitFilter,
    UnitStatus,
    UpdateBorrower,
    UpdateStaff,
)
from app.database import (
    bangkok_date,
    bangkok_today,
    connection,
    initialize_database,
    utc_now,
)
from app.errors import DomainError
from app.services.fake_services import (
    BorrowDraft,
    BorrowerRecord,
    HistoryEvent,
    InventoryEquipment,
    InventoryCategory,
    InventoryUnit,
    LocationRecord,
    LostCaseRecord,
    LoanRecord,
    StaffRecord,
)
from app.services.loans import SQLiteLoanService
from app.services.lost_cases import SQLiteLostCaseService
from app.services.master_data import (
    SQLiteBorrowerService,
    SQLiteEquipmentService,
    SQLiteLocationService,
    SQLiteStaffService,
    SQLiteUnitService,
)
from app.services.returns import SQLiteReturnService


class SQLiteInventoryAdapter:
    """Expose the current UI service API using persistent SQLite services."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        initialize_database(self.database_path)
        self.equipment = SQLiteEquipmentService(self.database_path)
        self.locations = SQLiteLocationService(self.database_path)
        self.units = SQLiteUnitService(self.database_path)
        self.staff = SQLiteStaffService(self.database_path)
        self.borrowers = SQLiteBorrowerService(self.database_path)
        self.loans = SQLiteLoanService(self.database_path)
        self.returns = SQLiteReturnService(self.database_path)
        self.lost_cases = SQLiteLostCaseService(self.database_path)

    def list_lost_cases(
        self, *, query: str | None = None, status: str | None = None
    ) -> list[LostCaseRecord]:
        with connection(self.database_path) as database:
            rows = database.execute(
                """
                SELECT lc.id, eu.asset_code, e.name AS equipment_name,
                       b.borrower_code, lc.reported_at, lc.assessed_value,
                       lc.approved_compensation, lc.resolution, lc.note,
                       s.staff_code AS approved_by_staff_code
                FROM lost_cases lc
                JOIN equipment_units eu ON eu.id = lc.equipment_unit_id
                JOIN equipment e ON e.id = eu.equipment_id
                JOIN borrow_items bi ON bi.id = lc.borrow_item_id
                JOIN borrow_transactions bt ON bt.id = bi.transaction_id
                JOIN borrowers b ON b.id = bt.borrower_id
                LEFT JOIN staff s ON s.id = lc.approved_by_staff_id
                ORDER BY lc.reported_at DESC, lc.id DESC
                """
            ).fetchall()
        cases = [
            LostCaseRecord(
                id=str(row["id"]),
                asset_code=row["asset_code"],
                equipment_name=row["equipment_name"],
                borrower_code=row["borrower_code"],
                reported_at=bangkok_date(row["reported_at"]).isoformat(),
                assessed_value=row["assessed_value"],
                approved_compensation=row["approved_compensation"],
                resolution=row["resolution"],
                approved_by_staff_code=row["approved_by_staff_code"],
                note=row["note"],
            )
            for row in rows
        ]
        keyword = (query or "").lower()
        if keyword:
            cases = [
                case
                for case in cases
                if keyword in case.asset_code.lower()
                or keyword in case.equipment_name.lower()
                or keyword in case.borrower_code.lower()
            ]
        if status == "open":
            cases = [case for case in cases if case.resolution is None]
        elif status == "resolved":
            cases = [case for case in cases if case.resolution is not None]
        return cases

    def resolve_lost_case(
        self,
        case_id: str,
        *,
        resolution: str,
        assessed_value: str,
        approved_compensation: str,
        staff_code: str,
        reason: str,
        note: str | None = None,
        recovered_outcome: str | None = None,
        location_id: str | None = None,
        replacement_asset_code: str | None = None,
        replacement_serial_number: str | None = None,
        replacement_purchase_price: str | None = None,
    ) -> LostCaseRecord | None:
        staff = self._staff_model(staff_code)
        if staff is None:
            return None
        replacement = None
        if resolution == "replaced":
            replacement = ReplacementUnit(
                asset_code=replacement_asset_code or "",
                acquired_at=bangkok_today(),
                location_id=int(location_id or ""),
                serial_number=replacement_serial_number or None,
                purchase_price=(
                    Decimal(replacement_purchase_price)
                    if replacement_purchase_price
                    else None
                ),
            )
        try:
            self.lost_cases.resolve_lost_case(
                int(case_id),
                ResolveLostCase(
                    resolution=LostResolution(resolution),
                    assessed_value=Decimal(assessed_value),
                    approved_compensation=Decimal(approved_compensation),
                    approved_by_staff_id=staff.id,
                    reason=reason,
                    note=note or None,
                    recovered_outcome=(
                        ReturnOutcome(recovered_outcome)
                        if recovered_outcome
                        else None
                    ),
                    location_id=int(location_id) if location_id else None,
                    replacement=replacement,
                ),
            )
        except (DomainError, ValueError):
            return None
        return next(
            (case for case in self.list_lost_cases() if case.id == case_id), None
        )

    def list_equipment(self) -> list[InventoryEquipment]:
        return [self._equipment_view(item) for item in self.equipment.search()]

    def list_categories(self) -> list[InventoryCategory]:
        with connection(self.database_path) as database:
            rows = database.execute(
                "SELECT id, name FROM equipment_categories ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return [
            InventoryCategory(id=str(row["id"]), name=row["name"])
            for row in rows
        ]

    def create_category(self, name: str) -> InventoryCategory | None:
        cleaned_name = name.strip()
        if not cleaned_name:
            return None
        try:
            with connection(self.database_path) as database:
                cursor = database.execute(
                    "INSERT INTO equipment_categories(name) VALUES (?)",
                    (cleaned_name,),
                )
                database.commit()
                category_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
        return InventoryCategory(id=str(category_id), name=cleaned_name)

    def list_locations(self) -> list[LocationRecord]:
        return [
            LocationRecord(
                id=str(item.id),
                location_code=item.location_code,
                label=" / ".join(filter(None, [item.building, item.room, item.cabinet, item.shelf])),
                status=item.status.value,
            )
            for item in self.locations.search()
        ]

    def create_equipment(
        self, name: str, equipment_code: str, category: str
    ) -> InventoryEquipment | None:
        category_record = next(
            (
                item
                for item in self.list_categories()
                if item.name.casefold() == category.casefold()
            ),
            None,
        )
        if category and category_record is None:
            category_record = self.create_category(category)
        try:
            item = self.equipment.create(
                CreateEquipment(
                    equipment_code=equipment_code,
                    name=name,
                    category=category or None,
                )
            )
        except DomainError:
            return None
        if category_record is not None:
            with connection(self.database_path) as database:
                database.execute(
                    "UPDATE equipment SET category_id = ? WHERE id = ?",
                    (int(category_record.id), item.id),
                )
                database.commit()
        return self._equipment_view(item)

    def create_inventory_item(
        self,
        *,
        name: str,
        category_id: str,
        asset_code: str,
        location: str,
    ) -> InventoryUnit | None:
        category = next(
            (item for item in self.list_categories() if item.id == category_id),
            None,
        )
        if category is None or self.get_unit_by_asset_code(asset_code) is not None:
            return None
        equipment = self.create_equipment(name, asset_code, category.name)
        if equipment is None:
            return None
        return self.create_unit(
            asset_code=asset_code,
            equipment_id=equipment.id,
            location=location,
        )

    def list_units(self) -> list[InventoryUnit]:
        return self.search_units()

    def search_units(
        self,
        keyword: str | None = None,
        status: str | None = None,
        category: str | None = None,
    ) -> list[InventoryUnit]:
        filters = UnitFilter(
            query=keyword or None,
            status=UnitStatus(status) if status else None,
            category=category or None,
        )
        return [self._unit_view(item) for item in self.units.search(filters)]

    def get_unit(self, asset_code: str) -> InventoryUnit | None:
        return next(
            (unit for unit in self.search_units(asset_code) if unit.asset_code == asset_code),
            None,
        )

    def get_unit_by_asset_code(self, asset_code: str) -> InventoryUnit | None:
        return self.get_unit(asset_code)

    def get_unit_by_id(self, unit_id: str) -> InventoryUnit | None:
        try:
            return self._unit_view(self.units.get(int(unit_id)))
        except (DomainError, ValueError):
            return None

    def create_unit(
        self,
        *,
        asset_code: str,
        equipment_id: str,
        location: str,
        status: str = "available",
    ) -> InventoryUnit | None:
        try:
            equipment_pk = self._resolve_equipment_id(equipment_id)
            location_id = self._ensure_location(location)
            staff_id = self._ensure_system_staff()
            unit = self.units.acquire(
                AcquireUnit(
                    asset_code=asset_code,
                    equipment_id=equipment_pk,
                    acquired_at=bangkok_today(),
                    current_location_id=location_id,
                    recorded_by_staff_id=staff_id,
                    reason="Created from inventory UI",
                )
            )
            if status != "available":
                return None
            return self._unit_view(unit)
        except (DomainError, ValueError):
            return None

    def update_unit_status(
        self,
        unit_id: str,
        status: str,
        *,
        location: str | None = None,
        reason: str | None = None,
    ) -> InventoryUnit | None:
        try:
            unit_pk = int(unit_id)
            if status == "retired":
                unit = self.units.retire(
                    unit_pk,
                    RetireUnit(
                        recorded_by_staff_id=self._ensure_system_staff(),
                        reason=reason or "Retired from inventory UI",
                    ),
                )
            elif status == "relocate":
                if not location:
                    return None
                unit = self.units.relocate(
                    unit_pk,
                    RelocateUnit(
                        location_id=self._ensure_location(location),
                        recorded_by_staff_id=self._ensure_system_staff(),
                        reason=reason or "Relocated from inventory UI",
                    ),
                )
            elif status == "maintenance":
                if not location:
                    return None
                unit = self.units.complete_repair(
                    unit_pk,
                    CompleteRepair(
                        location_id=self._ensure_location(location),
                        recorded_by_staff_id=self._ensure_system_staff(),
                        reason=reason or "Repair completed from inventory UI",
                    ),
                )
            elif status in {"lost_recovered", "lost_closed"}:
                case_id = self._open_lost_case_id(unit_pk)
                if case_id is None:
                    return None
                recovered = status == "lost_recovered"
                if recovered and not location:
                    return None
                self.lost_cases.resolve_lost_case(
                    case_id,
                    ResolveLostCase(
                        resolution=(
                            LostResolution.RECOVERED
                            if recovered
                            else LostResolution.WAIVED
                        ),
                        assessed_value=Decimal("0"),
                        approved_compensation=Decimal("0"),
                        approved_by_staff_id=self._ensure_system_staff(),
                        reason=reason or "Closed legacy lost record from inventory UI",
                        note="จัดการข้อมูลแจ้งหายเดิมจากหน้าคลังอุปกรณ์",
                        recovered_outcome=(
                            ReturnOutcome.AVAILABLE if recovered else None
                        ),
                        location_id=(
                            self._ensure_location(location or "")
                            if recovered
                            else None
                        ),
                    ),
                )
                unit = self.units.get(unit_pk)
            else:
                return None
            return self._unit_view(unit)
        except (DomainError, ValueError):
            return None

    def list_staff(self, *, include_inactive: bool = False) -> list[StaffRecord]:
        status = None if include_inactive else RecordStatus.ACTIVE
        return [self._staff_view(item) for item in self.staff.search(StaffFilter(status=status))]

    def get_staff(self, staff_code: str) -> StaffRecord | None:
        return next((item for item in self.list_staff(include_inactive=True) if item.staff_code == staff_code), None)

    def create_staff(self, staff_code: str, full_name: str, *, email: str | None = None, status: str = "active") -> StaffRecord | None:
        try:
            item = self.staff.create(CreateStaff(staff_code=staff_code, full_name=full_name, email=email))
            return self._staff_view(item)
        except DomainError:
            return None

    def update_staff(self, staff_code: str, *, full_name: str | None = None, email: str | None = None, status: str | None = None) -> StaffRecord | None:
        current = self._staff_model(staff_code)
        if current is None:
            return None
        try:
            item = self.staff.update(current.id, UpdateStaff(full_name=full_name or current.full_name, email=email if email is not None else current.email, phone=current.phone, status=RecordStatus(status or current.status.value)))
            return self._staff_view(item)
        except DomainError:
            return None

    def list_borrowers(self, *, include_inactive: bool = False) -> list[BorrowerRecord]:
        status = None if include_inactive else RecordStatus.ACTIVE
        return [self._borrower_view(item) for item in self.borrowers.search(BorrowerFilter(status=status))]

    def get_borrower(self, borrower_code: str) -> BorrowerRecord | None:
        return next((item for item in self.list_borrowers(include_inactive=True) if item.borrower_code == borrower_code), None)

    def create_borrower(self, borrower_code: str, full_name: str, *, department: str | None = None, email: str | None = None, status: str = "active") -> BorrowerRecord | None:
        try:
            item = self.borrowers.create(CreateBorrower(borrower_code=borrower_code, full_name=full_name, department=department, email=email))
            return self._borrower_view(item)
        except DomainError:
            return None

    def update_borrower(self, borrower_code: str, *, full_name: str | None = None, department: str | None = None, email: str | None = None, status: str | None = None) -> BorrowerRecord | None:
        current = self._borrower_model(borrower_code)
        if current is None:
            return None
        try:
            item = self.borrowers.update(current.id, UpdateBorrower(full_name=full_name or current.full_name, department=department if department is not None else current.department, email=email if email is not None else current.email, phone=current.phone, note=current.note, status=RecordStatus(status or current.status.value)))
            return self._borrower_view(item)
        except DomainError:
            return None

    def create_borrow_draft(self, *, borrower_code: str, staff_code: str, unit_ids: list[str], borrow_date: str, due_date: str, purpose: str) -> BorrowDraft | None:
        borrower = self._borrower_model(borrower_code)
        staff = self._staff_model(staff_code)
        if borrower is None or staff is None:
            return None
        try:
            loan = self.loans.create_draft(CreateDraftLoan(transaction_code=self._next_transaction_code(), borrower_id=borrower.id, recorded_by_staff_id=staff.id, borrow_date=date.fromisoformat(borrow_date), due_date=date.fromisoformat(due_date), unit_ids=tuple(int(value) for value in unit_ids), purpose=purpose or None))
            return self._draft_view(loan)
        except (DomainError, ValueError):
            return None

    def create_and_confirm_borrow(self, *, borrower_code: str, staff_code: str, unit_ids: list[str], borrow_date: str, due_date: str, purpose: str) -> BorrowDraft | None:
        borrower = self._borrower_model(borrower_code)
        staff = self._staff_model(staff_code)
        if borrower is None or staff is None:
            return None
        try:
            loan = self.loans.create_and_confirm(CreateDraftLoan(transaction_code=self._next_transaction_code(), borrower_id=borrower.id, recorded_by_staff_id=staff.id, borrow_date=date.fromisoformat(borrow_date), due_date=date.fromisoformat(due_date), unit_ids=tuple(int(value) for value in unit_ids), purpose=purpose or None))
            return self._draft_view(loan)
        except (DomainError, ValueError):
            return None

    def confirm_borrow_draft(self, draft_id: str) -> BorrowDraft | None:
        try:
            return self._draft_view(self.loans.confirm_loan(int(draft_id)))
        except (DomainError, ValueError):
            return None

    def list_loans(self, *, filter_type: str | None = None) -> list[LoanRecord]:
        with connection(self.database_path) as database:
            ids = [row["id"] for row in database.execute("SELECT id FROM borrow_transactions ORDER BY id DESC")]
        return self._apply_loan_filter(
            [self._loan_view(self.loans.get(loan_id)) for loan_id in ids], filter_type
        )

    def list_loans_for_borrower(
        self, borrower_id: int, *, filter_type: str | None = None
    ) -> list[LoanRecord]:
        with connection(self.database_path) as database:
            ids = [
                row["id"]
                for row in database.execute(
                    "SELECT id FROM borrow_transactions WHERE borrower_id = ? ORDER BY id DESC",
                    (borrower_id,),
                )
            ]
        return self._apply_loan_filter(
            [self._loan_view(self.loans.get(loan_id)) for loan_id in ids], filter_type
        )

    @staticmethod
    def _apply_loan_filter(
        loans: list[LoanRecord], filter_type: str | None
    ) -> list[LoanRecord]:
        today = bangkok_today()
        if filter_type == "today":
            return [loan for loan in loans if date.fromisoformat(loan.due_date) == today]
        if filter_type == "soon":
            return [loan for loan in loans if 1 <= (date.fromisoformat(loan.due_date) - today).days <= 3]
        if filter_type == "overdue":
            return [loan for loan in loans if date.fromisoformat(loan.due_date) < today and loan.status != "closed"]
        if filter_type == "partial":
            return [loan for loan in loans if loan.status == "partial"]
        return loans

    def get_loan(self, loan_id: str) -> LoanRecord | None:
        try:
            return self._loan_view(self.loans.get(int(loan_id)))
        except (DomainError, ValueError):
            return None

    def return_loan_units(self, loan_id: str, unit_ids: list[str], outcome: str, condition: str | None = None, *, staff_code: str | None = None, location_id: str | None = None) -> LoanRecord | None:
        try:
            loan_pk = int(loan_id)
            unit_pks = [int(value) for value in unit_ids]
            backend_outcome = ReturnOutcome.AVAILABLE if outcome == "returned" else ReturnOutcome(outcome)
            resolved_location_id = None if backend_outcome is ReturnOutcome.REPORTED_LOST else int(location_id or "")
            receiving_staff = self._staff_model(staff_code or "")
            if receiving_staff is None:
                return None
            with connection(self.database_path) as database:
                rows = database.execute(
                    "SELECT id, equipment_unit_id FROM borrow_items WHERE transaction_id = ?",
                    (loan_pk,),
                ).fetchall()
            item_by_unit = {row["equipment_unit_id"]: row["id"] for row in rows}
            commands = tuple(
                ReturnItemCommand(
                    borrow_item_id=item_by_unit[unit_id],
                    outcome=backend_outcome,
                    location_id=resolved_location_id,
                    condition_note=condition,
                )
                for unit_id in unit_pks
            )
            self.returns.record_return(
                RecordReturn(
                    loan_id=loan_pk,
                    returned_at=utc_now(),
                    received_by_staff_id=receiving_staff.id,
                    items=commands,
                    note=condition,
                )
            )
            return self.get_loan(loan_id)
        except (DomainError, KeyError, ValueError):
            return None

    def list_history(self, **filters: str | None) -> list[HistoryEvent]:
        with connection(self.database_path) as database:
            rows = database.execute(
                """
                SELECT 'borrow-' || bt.id || '-' || bi.id AS event_id,
                       'borrowed' AS event_type, bt.created_at AS occurred_at,
                       'ยืม ' || e.name || ' ' || eu.asset_code AS description,
                       b.borrower_code, s.staff_code, e.name AS equipment_name,
                       eu.asset_code, eu.id AS unit_id
                FROM borrow_items bi
                JOIN borrow_transactions bt ON bt.id = bi.transaction_id
                JOIN borrowers b ON b.id = bt.borrower_id
                JOIN staff s ON s.id = bt.recorded_by_staff_id
                JOIN equipment_units eu ON eu.id = bi.equipment_unit_id
                JOIN equipment e ON e.id = eu.equipment_id
                WHERE bt.status <> 'draft'
                UNION ALL
                SELECT 'return-' || r.id || '-' || ri.id, ri.outcome, r.returned_at,
                       'รับคืน ' || e.name || ' ' || eu.asset_code || ' (' || ri.outcome || ')',
                       b.borrower_code, s.staff_code, e.name, eu.asset_code, eu.id
                FROM return_items ri
                JOIN returns r ON r.id = ri.return_id
                JOIN borrow_items bi ON bi.id = ri.borrow_item_id
                JOIN borrow_transactions bt ON bt.id = bi.transaction_id
                JOIN borrowers b ON b.id = bt.borrower_id
                JOIN staff s ON s.id = r.received_by_staff_id
                JOIN equipment_units eu ON eu.id = bi.equipment_unit_id
                JOIN equipment e ON e.id = eu.equipment_id
                UNION ALL
                SELECT 'adjustment-' || ia.id, ia.action, ia.created_at,
                       ia.action || ': ' || e.name || ' ' || eu.asset_code || ' — ' || ia.reason,
                       '', s.staff_code, e.name, eu.asset_code, eu.id
                FROM inventory_adjustments ia
                JOIN staff s ON s.id = ia.staff_id
                JOIN equipment_units eu ON eu.id = ia.equipment_unit_id
                JOIN equipment e ON e.id = eu.equipment_id
                UNION ALL
                SELECT 'lost-' || lc.id, 'reported_lost', lc.reported_at,
                       'แจ้งสูญหาย ' || e.name || ' ' || eu.asset_code,
                       b.borrower_code, '', e.name, eu.asset_code, eu.id
                FROM lost_cases lc
                JOIN borrow_items bi ON bi.id = lc.borrow_item_id
                JOIN borrow_transactions bt ON bt.id = bi.transaction_id
                JOIN borrowers b ON b.id = bt.borrower_id
                JOIN equipment_units eu ON eu.id = lc.equipment_unit_id
                JOIN equipment e ON e.id = eu.equipment_id
                UNION ALL
                SELECT 'lost-resolution-' || lc.id, 'lost_resolved', lc.resolved_at,
                       'ปิดกรณีสูญหาย ' || e.name || ' ' || eu.asset_code || ' (' || lc.resolution || ')',
                       b.borrower_code, s.staff_code, e.name, eu.asset_code, eu.id
                FROM lost_cases lc
                JOIN borrow_items bi ON bi.id = lc.borrow_item_id
                JOIN borrow_transactions bt ON bt.id = bi.transaction_id
                JOIN borrowers b ON b.id = bt.borrower_id
                JOIN equipment_units eu ON eu.id = lc.equipment_unit_id
                JOIN equipment e ON e.id = eu.equipment_id
                JOIN staff s ON s.id = lc.approved_by_staff_id
                WHERE lc.resolution IS NOT NULL
                UNION ALL
                SELECT 'audit-' || al.id, 'audit_' || al.action, al.created_at,
                       'แก้ไข ' || al.entity_type || ' #' || al.entity_id || ' — ' || al.reason,
                       COALESCE(b.borrower_code, ''), s.staff_code, '', '', ''
                FROM audit_logs al
                JOIN staff s ON s.id = al.staff_id
                LEFT JOIN borrow_transactions bt
                  ON al.entity_type = 'loan' AND bt.id = al.entity_id
                LEFT JOIN borrowers b ON b.id = bt.borrower_id
                ORDER BY occurred_at DESC, event_id DESC
                """
            ).fetchall()

        events = [
            HistoryEvent(
                id=row["event_id"],
                event_type=row["event_type"],
                event_date=bangkok_date(row["occurred_at"]).isoformat(),
                description=row["description"],
                borrower_code=row["borrower_code"] or "",
                staff_code=row["staff_code"] or "",
                equipment_name=row["equipment_name"] or "",
                asset_code=row["asset_code"] or "",
                unit_id=str(row["unit_id"] or ""),
            )
            for row in rows
        ]
        borrower_query = (filters.get("borrower_query") or "").lower()
        equipment_query = (filters.get("equipment_query") or "").lower()
        asset_query = (filters.get("asset_code") or "").lower()
        return [
            event
            for event in events
            if (not borrower_query or borrower_query in event.borrower_code.lower() or borrower_query in event.description.lower())
            and (not equipment_query or equipment_query in event.equipment_name.lower() or equipment_query in event.description.lower())
            and (not asset_query or asset_query in event.asset_code.lower())
            and (not filters.get("start_date") or event.event_date >= filters["start_date"])
            and (not filters.get("end_date") or event.event_date <= filters["end_date"])
        ]

    def _unit_view(self, unit) -> InventoryUnit:
        equipment = self.equipment.get(unit.equipment_id)
        location = (
            "ยังไม่พบอุปกรณ์"
            if unit.status is UnitStatus.REPORTED_LOST
            else "อยู่กับผู้ยืม"
        )
        if unit.current_location_id is not None:
            location = self.locations.get(unit.current_location_id).room
        return InventoryUnit(id=str(unit.id), asset_code=unit.asset_code, equipment_name=equipment.name, status=unit.status.value, location=location, category=equipment.category or "", note=unit.note)

    @staticmethod
    def _equipment_view(item) -> InventoryEquipment:
        return InventoryEquipment(id=str(item.id), equipment_code=item.equipment_code, name=item.name, category=item.category or "", status=item.status.value)

    @staticmethod
    def _staff_view(item) -> StaffRecord:
        return StaffRecord(id=str(item.id), staff_code=item.staff_code, full_name=item.full_name, email=item.email, status=item.status.value)

    @staticmethod
    def _borrower_view(item) -> BorrowerRecord:
        return BorrowerRecord(id=str(item.id), borrower_code=item.borrower_code, full_name=item.full_name, department=item.department, email=item.email, status=item.status.value)

    def _draft_view(self, loan) -> BorrowDraft:
        borrower = self._borrower_model_by_id(loan.borrower_id)
        staff = self.staff.get(loan.recorded_by_staff_id)
        return BorrowDraft(id=str(loan.id), borrower_code=borrower.borrower_code, staff_code=staff.staff_code, unit_ids=[str(item.equipment_unit_id) for item in loan.items], borrow_date=loan.borrow_date.isoformat(), due_date=loan.due_date.isoformat(), purpose=loan.purpose or "", status=loan.status.value)

    def _loan_view(self, loan) -> LoanRecord:
        draft = self._draft_view(loan)
        with connection(self.database_path) as database:
            returned = [str(row["equipment_unit_id"]) for row in database.execute("SELECT bi.equipment_unit_id FROM borrow_items bi JOIN return_items ri ON ri.borrow_item_id = bi.id WHERE bi.transaction_id = ?", (loan.id,))]
        status = "closed" if loan.status.value == "completed" else "partial" if returned else loan.status.value
        return LoanRecord(
            id=draft.id,
            borrower_code=draft.borrower_code,
            staff_code=draft.staff_code,
            unit_ids=draft.unit_ids,
            borrow_date=draft.borrow_date,
            due_date=draft.due_date,
            purpose=draft.purpose,
            returned_unit_ids=returned,
            status=status,
        )

    def _staff_model(self, code: str):
        return next((item for item in self.staff.search(StaffFilter(query=code)) if item.staff_code == code), None)

    def _borrower_model(self, code: str):
        return next((item for item in self.borrowers.search(BorrowerFilter(query=code)) if item.borrower_code == code), None)

    def _borrower_model_by_id(self, borrower_id: int):
        return self.borrowers.get(borrower_id)

    def _resolve_equipment_id(self, raw_id: str) -> int:
        try:
            return int(raw_id)
        except ValueError:
            items = self.equipment.search(EquipmentFilter())
            if not items:
                raise ValueError("No equipment exists")
            return items[0].id

    def _ensure_location(self, room: str) -> int:
        existing = self.locations.search()
        match = next((item for item in existing if item.room == room), None)
        if match:
            return match.id
        return self.locations.create(CreateLocation(location_code=f"LOC-{len(existing) + 1:04d}", room=room)).id

    def _ensure_system_staff(self) -> int:
        existing = self._staff_model("SYSTEM")
        if existing:
            return existing.id
        return self.staff.create(CreateStaff(staff_code="SYSTEM", full_name="System Operator")).id

    def _open_lost_case_id(self, unit_id: int) -> int | None:
        with connection(self.database_path) as database:
            row = database.execute(
                """
                SELECT id FROM lost_cases
                WHERE equipment_unit_id = ? AND resolution IS NULL
                ORDER BY id DESC LIMIT 1
                """,
                (unit_id,),
            ).fetchone()
        return row["id"] if row is not None else None

    def _next_transaction_code(self) -> str:
        with connection(self.database_path) as database:
            count = database.execute("SELECT COUNT(*) FROM borrow_transactions").fetchone()[0]
        return f"LOAN-{count + 1:06d}"
