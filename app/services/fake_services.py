from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InventoryUnit:
    id: str
    asset_code: str
    equipment_name: str
    status: str
    location: str
    note: str | None = None


@dataclass(frozen=True)
class InventoryEquipment:
    id: str
    equipment_code: str
    name: str
    category: str
    status: str = "active"


@dataclass(frozen=True)
class StaffRecord:
    id: str
    staff_code: str
    full_name: str
    email: str | None = None
    status: str = "active"


@dataclass(frozen=True)
class BorrowerRecord:
    id: str
    borrower_code: str
    full_name: str
    department: str | None = None
    email: str | None = None
    status: str = "active"


@dataclass(frozen=True)
class BorrowDraft:
    id: str
    borrower_code: str
    staff_code: str
    unit_ids: list[str]
    borrow_date: str
    due_date: str
    purpose: str
    status: str = "draft"


class FakeInventoryService:
    def __init__(self) -> None:
        self._equipment = [
            InventoryEquipment(id="eq-1", equipment_code="EQ-100", name="Laptop", category="IT"),
            InventoryEquipment(id="eq-2", equipment_code="EQ-200", name="Microscope", category="Research"),
        ]
        self._units = [
            InventoryUnit(id="unit-1", asset_code="AST-001", equipment_name="Laptop", status="available", location="Lab A - Shelf 1"),
            InventoryUnit(id="unit-2", asset_code="AST-002", equipment_name="Laptop", status="borrowed", location="With Borrower"),
            InventoryUnit(id="unit-3", asset_code="AST-003", equipment_name="Microscope", status="maintenance", location="Repair Room"),
            InventoryUnit(id="unit-4", asset_code="AST-004", equipment_name="Microscope", status="reported_lost", location="Lost Case"),
            InventoryUnit(id="unit-5", asset_code="AST-005", equipment_name="Laptop", status="retired", location="Archive"),
        ]
        self._staff = [
            StaffRecord(id="staff-1", staff_code="ST-001", full_name="Ada Lovelace", email="ada@example.com", status="active"),
            StaffRecord(id="staff-2", staff_code="ST-002", full_name="Grace Hopper", email="grace@example.com", status="inactive"),
        ]
        self._borrowers = [
            BorrowerRecord(id="borrower-1", borrower_code="BR-001", full_name="Lin Chen", department="Biochemistry", email="lin@example.com", status="active"),
            BorrowerRecord(id="borrower-2", borrower_code="BR-002", full_name="Mina Patel", department="Physics", email="mina@example.com", status="inactive"),
        ]
        self._borrow_drafts: list[BorrowDraft] = []

    def list_equipment(self) -> list[InventoryEquipment]:
        return list(self._equipment)

    def list_units(self) -> list[InventoryUnit]:
        return list(self._units)

    def get_unit(self, asset_code: str) -> InventoryUnit | None:
        for unit in self._units:
            if unit.asset_code == asset_code:
                return unit
        return None

    def get_unit_by_asset_code(self, asset_code: str) -> InventoryUnit | None:
        return self.get_unit(asset_code)

    def create_equipment(self, name: str, equipment_code: str, category: str) -> InventoryEquipment:
        equipment = InventoryEquipment(
            id=f"eq-{len(self._equipment) + 1}",
            equipment_code=equipment_code,
            name=name,
            category=category,
        )
        self._equipment.append(equipment)
        return equipment

    def create_unit(self, *, asset_code: str, equipment_id: str, location: str, status: str = "available") -> InventoryUnit | None:
        if any(unit.asset_code == asset_code for unit in self._units):
            return None

        equipment_name = next((item.name for item in self._equipment if item.id == equipment_id), "Unknown")
        unit = InventoryUnit(
            id=f"unit-{len(self._units) + 1}",
            asset_code=asset_code,
            equipment_name=equipment_name,
            status=status,
            location=location,
        )
        self._units.append(unit)
        return unit

    def update_unit_status(self, unit_id: str, status: str, *, location: str | None = None, reason: str | None = None) -> InventoryUnit | None:
        for index, unit in enumerate(self._units):
            if unit.id != unit_id:
                continue
            updated_unit = InventoryUnit(
                id=unit.id,
                asset_code=unit.asset_code,
                equipment_name=unit.equipment_name,
                status=status,
                location=location or unit.location,
                note=reason,
            )
            self._units[index] = updated_unit
            return updated_unit
        return None

    def search_units(self, keyword: str | None = None, status: str | None = None) -> list[InventoryUnit]:
        results = list(self._units)
        if keyword:
            keyword = keyword.lower()
            results = [unit for unit in results if keyword in unit.equipment_name.lower() or keyword in unit.asset_code.lower()]
        if status:
            results = [unit for unit in results if unit.status == status]
        return results

    def list_staff(self, *, include_inactive: bool = False) -> list[StaffRecord]:
        if include_inactive:
            return list(self._staff)
        return [staff for staff in self._staff if staff.status == "active"]

    def get_staff(self, staff_code: str) -> StaffRecord | None:
        return next((staff for staff in self._staff if staff.staff_code == staff_code), None)

    def create_staff(self, staff_code: str, full_name: str, *, email: str | None = None, status: str = "active") -> StaffRecord | None:
        if self.get_staff(staff_code) is not None:
            return None
        staff = StaffRecord(id=f"staff-{len(self._staff) + 1}", staff_code=staff_code, full_name=full_name, email=email, status=status)
        self._staff.append(staff)
        return staff

    def update_staff(self, staff_code: str, *, full_name: str | None = None, email: str | None = None, status: str | None = None) -> StaffRecord | None:
        for index, staff in enumerate(self._staff):
            if staff.staff_code != staff_code:
                continue
            updated = StaffRecord(
                id=staff.id,
                staff_code=staff.staff_code,
                full_name=full_name or staff.full_name,
                email=email if email is not None else staff.email,
                status=status or staff.status,
            )
            self._staff[index] = updated
            return updated
        return None

    def list_borrowers(self, *, include_inactive: bool = False) -> list[BorrowerRecord]:
        if include_inactive:
            return list(self._borrowers)
        return [borrower for borrower in self._borrowers if borrower.status == "active"]

    def get_borrower(self, borrower_code: str) -> BorrowerRecord | None:
        return next((borrower for borrower in self._borrowers if borrower.borrower_code == borrower_code), None)

    def create_borrower(self, borrower_code: str, full_name: str, *, department: str | None = None, email: str | None = None, status: str = "active") -> BorrowerRecord | None:
        if self.get_borrower(borrower_code) is not None:
            return None
        borrower = BorrowerRecord(id=f"borrower-{len(self._borrowers) + 1}", borrower_code=borrower_code, full_name=full_name, department=department, email=email, status=status)
        self._borrowers.append(borrower)
        return borrower

    def update_borrower(self, borrower_code: str, *, full_name: str | None = None, department: str | None = None, email: str | None = None, status: str | None = None) -> BorrowerRecord | None:
        for index, borrower in enumerate(self._borrowers):
            if borrower.borrower_code != borrower_code:
                continue
            updated = BorrowerRecord(
                id=borrower.id,
                borrower_code=borrower.borrower_code,
                full_name=full_name or borrower.full_name,
                department=department if department is not None else borrower.department,
                email=email if email is not None else borrower.email,
                status=status or borrower.status,
            )
            self._borrowers[index] = updated
            return updated
        return None

    def create_borrow_draft(self, *, borrower_code: str, staff_code: str, unit_ids: list[str], borrow_date: str, due_date: str, purpose: str) -> BorrowDraft | None:
        if self.get_borrower(borrower_code) is None or self.get_staff(staff_code) is None:
            return None

        units = [self.get_unit_by_id(unit_id) for unit_id in unit_ids]
        if any(unit is None or unit.status != "available" for unit in units):
            return None

        draft = BorrowDraft(
            id=f"draft-{len(self._borrow_drafts) + 1}",
            borrower_code=borrower_code,
            staff_code=staff_code,
            unit_ids=unit_ids,
            borrow_date=borrow_date,
            due_date=due_date,
            purpose=purpose,
        )
        self._borrow_drafts.append(draft)
        return draft

    def confirm_borrow_draft(self, draft_id: str) -> BorrowDraft | None:
        for index, draft in enumerate(self._borrow_drafts):
            if draft.id != draft_id:
                continue
            for unit_id in draft.unit_ids:
                self.update_unit_status(unit_id, "borrowed")
            confirmed = BorrowDraft(
                id=draft.id,
                borrower_code=draft.borrower_code,
                staff_code=draft.staff_code,
                unit_ids=draft.unit_ids,
                borrow_date=draft.borrow_date,
                due_date=draft.due_date,
                purpose=draft.purpose,
                status="active",
            )
            self._borrow_drafts[index] = confirmed
            return confirmed
        return None

    def get_unit_by_id(self, unit_id: str) -> InventoryUnit | None:
        for unit in self._units:
            if unit.id == unit_id:
                return unit
        return None
