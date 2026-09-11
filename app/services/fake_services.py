from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta

from app.contracts import (
    AppUser,
    ChangePasswordCommand,
    CreateLostReport,
    CreateUserCommand,
    LoginCommand,
    LostReport,
    LostReportStatus,
    RecordStatus,
    RegisterLineUser,
    ReviewLostReport,
    Role,
)
from app.database import bangkok_today, utc_now
from app.errors import (
    AuthenticationError,
    DuplicateCodeError,
    InactiveRecordError,
    NotFoundError,
    ReportAlreadyReviewed,
    ValidationError,
)
from app.security import hash_password, validate_password_strength
from app.services.auth_service import (
    INACTIVE_USER_MESSAGE,
    WRONG_CREDENTIALS_MESSAGE,
    apply_change_password,
    check_manage_users,
    verify_login,
)


@dataclass(frozen=True)
class InventoryUnit:
    id: str
    asset_code: str
    equipment_name: str
    status: str
    location: str
    category: str = ""
    note: str | None = None


@dataclass(frozen=True)
class InventoryEquipment:
    id: str
    equipment_code: str
    name: str
    category: str
    status: str = "active"


@dataclass(frozen=True)
class InventoryCategory:
    id: str
    name: str


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
class LocationRecord:
    id: str
    location_code: str
    label: str
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


@dataclass(frozen=True)
class LoanRecord:
    id: str
    borrower_code: str
    staff_code: str
    unit_ids: list[str]
    borrow_date: str
    due_date: str
    purpose: str
    returned_unit_ids: list[str] = field(default_factory=list)
    status: str = "active"


@dataclass(frozen=True)
class HistoryEvent:
    id: str
    event_type: str
    event_date: str
    description: str
    borrower_code: str = ""
    staff_code: str = ""
    equipment_name: str = ""
    asset_code: str = ""
    unit_id: str = ""


@dataclass(frozen=True)
class LostCaseRecord:
    id: str
    asset_code: str
    equipment_name: str
    borrower_code: str
    reported_at: str
    assessed_value: str | None = None
    approved_compensation: str | None = None
    resolution: str | None = None
    approved_by_staff_code: str | None = None
    note: str | None = None


class FakeInventoryService:
    def __init__(self) -> None:
        self._categories = [
            InventoryCategory(id="category-1", name="IT"),
            InventoryCategory(id="category-2", name="Research"),
        ]
        self._equipment = [
            InventoryEquipment(id="eq-1", equipment_code="EQ-100", name="Laptop", category="IT"),
            InventoryEquipment(id="eq-2", equipment_code="EQ-200", name="Microscope", category="Research"),
        ]
        self._units = [
            InventoryUnit(id="unit-1", asset_code="AST-001", equipment_name="Laptop", status="available", location="คลังอุปกรณ์ - ชั้น 1", category="คอมพิวเตอร์และไอที"),
            InventoryUnit(id="unit-2", asset_code="AST-002", equipment_name="Laptop", status="borrowed", location="With Borrower", category="IT"),
            InventoryUnit(id="unit-3", asset_code="AST-003", equipment_name="Microscope", status="maintenance", location="Repair Room", category="Research"),
            InventoryUnit(id="unit-4", asset_code="AST-004", equipment_name="Microscope", status="reported_lost", location="Lost Case", category="Research"),
            InventoryUnit(id="unit-5", asset_code="AST-005", equipment_name="Laptop", status="retired", location="Archive", category="IT"),
        ]
        self._staff = [
            StaffRecord(id="staff-1", staff_code="ST-001", full_name="Ada Lovelace", email="ada@example.com", status="active"),
            StaffRecord(id="staff-2", staff_code="ST-002", full_name="Grace Hopper", email="grace@example.com", status="inactive"),
        ]
        self._borrowers = [
            BorrowerRecord(id="borrower-1", borrower_code="BR-001", full_name="สมชาย ใจดี", department="งานวิจัยและพัฒนา", email="somchai@example.com", status="active"),
            BorrowerRecord(id="borrower-2", borrower_code="BR-002", full_name="Mina Patel", department="Physics", email="mina@example.com", status="inactive"),
        ]
        self._borrow_drafts: list[BorrowDraft] = []
        self._loans: list[LoanRecord] = [
            LoanRecord(
                id="loan-1",
                borrower_code="BR-001",
                staff_code="ST-001",
                unit_ids=["unit-2"],
                borrow_date=(bangkok_today() - timedelta(days=3)).isoformat(),
                due_date=(bangkok_today() + timedelta(days=4)).isoformat(),
                purpose="Team demo",
                returned_unit_ids=[],
                status="active",
            )
        ]
        self._history: list[HistoryEvent] = [
            HistoryEvent(
                id="hist-1",
                event_type="borrowed",
                event_date=(bangkok_today() - timedelta(days=3)).isoformat(),
                description="Lin Chen ยืม Laptop AST-002",
                borrower_code="BR-001",
                staff_code="ST-001",
                equipment_name="Laptop",
                asset_code="AST-002",
                unit_id="unit-2",
            ),
            HistoryEvent(
                id="hist-2",
                event_type="maintenance",
                event_date=(bangkok_today() - timedelta(days=5)).isoformat(),
                description="Microscope AST-003 ส่งซ่อม",
                staff_code="ST-001",
                equipment_name="Microscope",
                asset_code="AST-003",
                unit_id="unit-3",
            ),
        ]
        self._lost_cases = [
            LostCaseRecord(
                id="case-1",
                asset_code="AST-004",
                equipment_name="Microscope",
                borrower_code="BR-001",
                reported_at=bangkok_today().isoformat(),
            )
        ]
        self._lost_reports: list[LostReport] = []

    def list_lost_cases(
        self, *, query: str | None = None, status: str | None = None
    ) -> list[LostCaseRecord]:
        cases = list(self._lost_cases)
        if query:
            keyword = query.lower()
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
        **_: object,
    ) -> LostCaseRecord | None:
        if not assessed_value or not approved_compensation or not reason.strip():
            return None
        if self.get_staff(staff_code) is None:
            return None
        for index, case in enumerate(self._lost_cases):
            if case.id != case_id or case.resolution is not None:
                continue
            resolved = LostCaseRecord(
                id=case.id,
                asset_code=case.asset_code,
                equipment_name=case.equipment_name,
                borrower_code=case.borrower_code,
                reported_at=case.reported_at,
                assessed_value=assessed_value,
                approved_compensation=approved_compensation,
                resolution=resolution,
                approved_by_staff_code=staff_code,
                note=note,
            )
            self._lost_cases[index] = resolved
            return resolved
        return None

    def create_lost_report(self, command: CreateLostReport) -> LostReport:
        if not 1 <= command.borrower_id <= len(self._borrowers):
            raise NotFoundError("borrower", command.borrower_id)
        borrower = self._borrowers[command.borrower_id - 1]
        if borrower.status != "active":
            raise InactiveRecordError("borrower", command.borrower_id)
        borrowed_unit_ids = {
            unit_id
            for loan in self._loans
            if loan.borrower_code == borrower.borrower_code
            for unit_id in loan.unit_ids
            if unit_id not in loan.returned_unit_ids
        }
        if f"unit-{command.equipment_unit_id}" not in borrowed_unit_ids:
            raise ValidationError(
                "equipment unit is not currently borrowed by this borrower",
                field="equipment_unit_id",
            )
        reported_at = utc_now()
        report = LostReport(
            id=len(self._lost_reports) + 1,
            borrower_id=command.borrower_id,
            equipment_unit_id=command.equipment_unit_id,
            reported_at=reported_at,
            lost_date=command.lost_date,
            location=command.location,
            description=command.description,
            status=LostReportStatus.PENDING,
            reviewed_by_staff_id=None,
            reviewed_at=None,
            review_note=None,
            created_at=reported_at,
        )
        self._lost_reports.append(report)
        return report

    def list_pending_lost_reports(self) -> list[LostReport]:
        return [
            report
            for report in self._lost_reports
            if report.status is LostReportStatus.PENDING
        ]

    def list_lost_reports_for_borrower(
        self, borrower_id: int
    ) -> list[LostReport]:
        return [
            report
            for report in self._lost_reports
            if report.borrower_id == borrower_id
        ]

    def review_lost_report(
        self, report_id: int, command: ReviewLostReport
    ) -> LostReport:
        for index, report in enumerate(self._lost_reports):
            if report.id != report_id:
                continue
            if report.status is not LostReportStatus.PENDING:
                raise ReportAlreadyReviewed(report_id, report.status.value)
            if not 1 <= command.reviewed_by_staff_id <= len(self._staff):
                raise NotFoundError("staff", command.reviewed_by_staff_id)
            staff = self._staff[command.reviewed_by_staff_id - 1]
            if staff.status != "active":
                raise InactiveRecordError("staff", command.reviewed_by_staff_id)
            reviewed = replace(
                report,
                status=(
                    LostReportStatus.APPROVED
                    if command.approved
                    else LostReportStatus.REJECTED
                ),
                reviewed_by_staff_id=command.reviewed_by_staff_id,
                reviewed_at=utc_now(),
                review_note=command.review_note,
            )
            self._lost_reports[index] = reviewed
            if command.approved:
                unit = self._set_unit_state(
                    f"unit-{report.equipment_unit_id}", "reported_lost"
                )
                assert unit is not None
                borrower_code = self._borrowers[
                    report.borrower_id - 1
                ].borrower_code
                self._lost_cases.append(
                    LostCaseRecord(
                        id=f"case-{len(self._lost_cases) + 1}",
                        asset_code=unit.asset_code,
                        equipment_name=unit.equipment_name,
                        borrower_code=borrower_code,
                        reported_at=bangkok_today().isoformat(),
                        note=command.review_note,
                    )
                )
            return reviewed
        raise NotFoundError("lost_report", report_id)

    def list_history(
        self,
        *,
        borrower_query: str | None = None,
        equipment_query: str | None = None,
        asset_code: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[HistoryEvent]:
        results = list(self._history)
        if borrower_query:
            q = borrower_query.lower()
            results = [e for e in results if q in e.borrower_code.lower() or q in e.description.lower()]
        if equipment_query:
            q = equipment_query.lower()
            results = [e for e in results if q in e.equipment_name.lower() or q in e.description.lower()]
        if asset_code:
            results = [e for e in results if asset_code.lower() in e.asset_code.lower()]
        if start_date:
            results = [e for e in results if e.event_date >= start_date]
        if end_date:
            results = [e for e in results if e.event_date <= end_date]
        return results

    def list_equipment(self) -> list[InventoryEquipment]:
        return list(self._equipment)

    def list_categories(self) -> list[InventoryCategory]:
        return list(self._categories)

    def create_category(self, name: str) -> InventoryCategory | None:
        cleaned_name = name.strip()
        if not cleaned_name or any(
            item.name.casefold() == cleaned_name.casefold()
            for item in self._categories
        ):
            return None
        category = InventoryCategory(
            id=f"category-{len(self._categories) + 1}", name=cleaned_name
        )
        self._categories.append(category)
        return category

    def list_locations(self) -> list[LocationRecord]:
        labels = sorted({unit.location for unit in self._units if unit.location != "With Borrower"})
        return [LocationRecord(id=f"location-{index}", location_code=f"LOC-{index:03d}", label=label) for index, label in enumerate(labels, 1)]

    def list_units(self) -> list[InventoryUnit]:
        return list(self._units)

    def get_unit(self, asset_code: str) -> InventoryUnit | None:
        for unit in self._units:
            if unit.asset_code == asset_code:
                return unit
        return None

    def get_unit_by_asset_code(self, asset_code: str) -> InventoryUnit | None:
        return self.get_unit(asset_code)

    def create_equipment(
        self, name: str, equipment_code: str, category: str
    ) -> InventoryEquipment | None:
        if any(item.equipment_code == equipment_code for item in self._equipment):
            return None
        if not any(
            item.name.casefold() == category.casefold()
            for item in self._categories
        ):
            self.create_category(category)
        equipment = InventoryEquipment(
            id=f"eq-{len(self._equipment) + 1}",
            equipment_code=equipment_code,
            name=name,
            category=category,
        )
        self._equipment.append(equipment)
        return equipment

    def create_inventory_item(
        self,
        *,
        name: str,
        category_id: str,
        asset_code: str,
        location: str,
    ) -> InventoryUnit | None:
        category = next(
            (item for item in self._categories if item.id == category_id), None
        )
        if category is None or any(
            unit.asset_code == asset_code for unit in self._units
        ):
            return None
        equipment = self.create_equipment(name, asset_code, category.name)
        if equipment is None:
            return None
        return self.create_unit(
            asset_code=asset_code,
            equipment_id=equipment.id,
            location=location,
        )

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
            category=next(
                (item.category for item in self._equipment if item.id == equipment_id),
                "",
            ),
        )
        self._units.append(unit)
        return unit

    def update_unit_status(self, unit_id: str, status: str, *, location: str | None = None, reason: str | None = None) -> InventoryUnit | None:
        for index, unit in enumerate(self._units):
            if unit.id != unit_id:
                continue
            if status == "relocate":
                target_status = unit.status
            elif status == "maintenance":
                if unit.status != "maintenance":
                    return None
                target_status = "available"
            elif status == "retired":
                if unit.status != "available":
                    return None
                target_status = "retired"
            elif status == "lost_recovered":
                if unit.status != "reported_lost" or not location:
                    return None
                target_status = "available"
            elif status == "lost_closed":
                if unit.status != "reported_lost":
                    return None
                target_status = "retired"
            else:
                return None
            updated_unit = InventoryUnit(
                id=unit.id,
                asset_code=unit.asset_code,
                equipment_name=unit.equipment_name,
                status=target_status,
                location=location or unit.location,
                category=unit.category,
                note=reason,
            )
            self._units[index] = updated_unit
            if status in {"lost_recovered", "lost_closed"}:
                resolution = "recovered" if status == "lost_recovered" else "waived"
                for case_index, case in enumerate(self._lost_cases):
                    if case.asset_code == unit.asset_code and case.resolution is None:
                        self._lost_cases[case_index] = LostCaseRecord(
                            id=case.id,
                            asset_code=case.asset_code,
                            equipment_name=case.equipment_name,
                            borrower_code=case.borrower_code,
                            reported_at=case.reported_at,
                            assessed_value="0",
                            approved_compensation="0",
                            resolution=resolution,
                            approved_by_staff_code="SYSTEM",
                            note=reason,
                        )
                        break
            return updated_unit
        return None

    def _set_unit_state(
        self,
        unit_id: str,
        status: str,
        *,
        location: str | None = None,
        reason: str | None = None,
    ) -> InventoryUnit | None:
        for index, unit in enumerate(self._units):
            if unit.id != unit_id:
                continue
            updated = InventoryUnit(
                id=unit.id,
                asset_code=unit.asset_code,
                equipment_name=unit.equipment_name,
                status=status,
                location=location or unit.location,
                category=unit.category,
                note=reason,
            )
            self._units[index] = updated
            return updated
        return None

    def search_units(
        self,
        keyword: str | None = None,
        status: str | None = None,
        category: str | None = None,
    ) -> list[InventoryUnit]:
        results = list(self._units)
        if keyword:
            keyword = keyword.lower()
            results = [
                unit
                for unit in results
                if keyword in unit.equipment_name.lower()
                or keyword in unit.asset_code.lower()
                or keyword in (unit.category or "").lower()
            ]
        if status:
            results = [unit for unit in results if unit.status == status]
        if category:
            results = [
                unit
                for unit in results
                if (unit.category or "").casefold() == category.casefold()
            ]
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
                self._set_unit_state(unit_id, "borrowed", location="With Borrower")
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
            self._loans.append(
                LoanRecord(
                    id=f"loan-{len(self._loans) + 1}",
                    borrower_code=draft.borrower_code,
                    staff_code=draft.staff_code,
                    unit_ids=draft.unit_ids,
                    borrow_date=draft.borrow_date,
                    due_date=draft.due_date,
                    purpose=draft.purpose,
                    returned_unit_ids=[],
                    status="active",
                )
            )
            return confirmed
        return None

    def create_and_confirm_borrow(self, *, borrower_code: str, staff_code: str, unit_ids: list[str], borrow_date: str, due_date: str, purpose: str) -> BorrowDraft | None:
        if self.get_borrower(borrower_code) is None or self.get_staff(staff_code) is None:
            return None
        units = [self.get_unit_by_id(unit_id) for unit_id in unit_ids]
        if not unit_ids or any(
            unit is None or unit.status != "available" for unit in units
        ):
            return None

        confirmed = BorrowDraft(
            id=f"draft-{len(self._borrow_drafts) + 1}",
            borrower_code=borrower_code,
            staff_code=staff_code,
            unit_ids=unit_ids,
            borrow_date=borrow_date,
            due_date=due_date,
            purpose=purpose,
            status="active",
        )
        for unit_id in unit_ids:
            self._set_unit_state(unit_id, "borrowed", location="With Borrower")
        self._borrow_drafts.append(confirmed)
        self._loans.append(
            LoanRecord(
                id=f"loan-{len(self._loans) + 1}",
                borrower_code=borrower_code,
                staff_code=staff_code,
                unit_ids=unit_ids,
                borrow_date=borrow_date,
                due_date=due_date,
                purpose=purpose,
            )
        )
        return confirmed

    def list_loans(self, *, filter_type: str | None = None) -> list[LoanRecord]:
        loans = list(self._loans)
        if filter_type == "today":
            today = bangkok_today()
            loans = [loan for loan in loans if date.fromisoformat(loan.due_date) == today]
        elif filter_type == "soon":
            today = bangkok_today()
            soon = today + timedelta(days=7)
            loans = [loan for loan in loans if today < date.fromisoformat(loan.due_date) <= soon]
        elif filter_type == "overdue":
            today = bangkok_today()
            loans = [loan for loan in loans if date.fromisoformat(loan.due_date) < today]
        elif filter_type == "partial":
            loans = [loan for loan in loans if loan.status == "partial"]
        return loans

    def list_loans_for_borrower(
        self, borrower_id: int, *, filter_type: str | None = None
    ) -> list[LoanRecord]:
        if not 1 <= borrower_id <= len(self._borrowers):
            return []
        borrower = self._borrowers[borrower_id - 1]
        return [
            loan
            for loan in self.list_loans(filter_type=filter_type)
            if loan.borrower_code == borrower.borrower_code
        ]

    def get_loan(self, loan_id: str) -> LoanRecord | None:
        return next((loan for loan in self._loans if loan.id == loan_id), None)

    def return_loan_units(self, loan_id: str, unit_ids: list[str], outcome: str, condition: str | None = None, *, staff_code: str | None = None, location_id: str | None = None) -> LoanRecord | None:
        loan = self.get_loan(loan_id)
        if loan is None:
            return None

        if not unit_ids:
            return None

        returned = set(loan.returned_unit_ids)
        updated_units = list(loan.returned_unit_ids)
        for unit_id in unit_ids:
            if unit_id not in loan.unit_ids or unit_id in returned:
                continue
            self._set_unit_state(unit_id, "available" if outcome == "returned" else "maintenance" if outcome == "maintenance" else "reported_lost", reason=condition)
            updated_units.append(unit_id)
            returned.add(unit_id)

        if not updated_units:
            return None

        remaining = [unit_id for unit_id in loan.unit_ids if unit_id not in returned]
        status = "closed" if not remaining else "partial" if len(returned) > 0 else "active"
        updated_loan = LoanRecord(
            id=loan.id,
            borrower_code=loan.borrower_code,
            staff_code=loan.staff_code,
            unit_ids=loan.unit_ids,
            borrow_date=loan.borrow_date,
            due_date=loan.due_date,
            purpose=loan.purpose,
            returned_unit_ids=updated_units,
            status=status,
        )
        self._loans = [updated_loan if item.id == loan_id else item for item in self._loans]
        return updated_loan

    def get_unit_by_id(self, unit_id: str) -> InventoryUnit | None:
        for unit in self._units:
            if unit.id == unit_id:
                return unit
        return None


class FakeAuthService:
    def __init__(self) -> None:
        self._next_id = 2
        self._users: list[AppUser] = [
            AppUser(
                id=1,
                role=Role.ADMIN,
                display_name="ผู้ดูแลระบบ",
                email="admin@lab.local",
                staff_id=None,
                borrower_id=1,
                status=RecordStatus.ACTIVE,
                must_change_password=True,
                last_login_at=None,
            ),
            AppUser(
                id=2,
                role=Role.USER,
                display_name="ผู้ยืมทดสอบ",
                email="borrower@lab.local",
                staff_id=None,
                borrower_id=1,
                status=RecordStatus.ACTIVE,
                must_change_password=False,
                last_login_at=None,
            ),
        ]
        self._passwords: dict[int, str] = {
            1: hash_password("admin123"),
            2: hash_password("borrow123"),
        }
        self._line_subs: dict[int, str] = {}

    def authenticate(self, command: LoginCommand) -> AppUser:
        identity = command.identity.strip().casefold()
        user = next(
            (
                candidate
                for candidate in self._users
                if candidate.email is not None
                and candidate.email.casefold() == identity
            ),
            None,
        )
        if user is None:
            raise AuthenticationError(WRONG_CREDENTIALS_MESSAGE)
        verify_login(command.password, self._passwords.get(user.id))
        if user.status is not RecordStatus.ACTIVE:
            raise AuthenticationError(INACTIVE_USER_MESSAGE)
        logged_in = replace(user, last_login_at=utc_now())
        self._users = [
            logged_in if candidate.id == user.id else candidate
            for candidate in self._users
        ]
        return logged_in

    def get(self, user_id: int) -> AppUser | None:
        return next(
            (candidate for candidate in self._users if candidate.id == user_id), None
        )

    def find_by_line_sub(self, line_sub: str) -> AppUser | None:
        user_id = next(
            (
                candidate_id
                for candidate_id, sub in self._line_subs.items()
                if sub == line_sub
            ),
            None,
        )
        return self.get(user_id) if user_id is not None else None

    def list_users(self) -> list[AppUser]:
        return list(self._users)

    def create_user(self, command: CreateUserCommand, *, actor: AppUser) -> AppUser:
        check_manage_users(actor)
        email = command.email.strip() if command.email else None
        if email is not None and any(
            candidate.email is not None
            and candidate.email.casefold() == email.casefold()
            for candidate in self._users
        ):
            raise DuplicateCodeError("email", email)
        password_hash = hash_password(command.password) if command.password else None
        self._next_id += 1
        user = AppUser(
            id=self._next_id,
            role=command.role,
            display_name=command.display_name.strip(),
            email=email,
            staff_id=command.staff_id,
            borrower_id=command.borrower_id,
            status=RecordStatus.ACTIVE,
            must_change_password=password_hash is None,
            last_login_at=None,
        )
        self._users.append(user)
        if password_hash is not None:
            self._passwords[user.id] = password_hash
        return user

    def set_user_status(
        self, user_id: int, status: RecordStatus, *, actor: AppUser
    ) -> None:
        check_manage_users(actor)
        if self.get(user_id) is None:
            raise NotFoundError("user", user_id)
        self._users = [
            replace(candidate, status=status) if candidate.id == user_id else candidate
            for candidate in self._users
        ]

    def set_user_role(
        self, user_id: int, new_role: Role, *, actor: AppUser
    ) -> AppUser:
        check_manage_users(actor)
        if self.get(user_id) is None:
            raise NotFoundError("user", user_id)
        self._users = [
            replace(candidate, role=new_role) if candidate.id == user_id else candidate
            for candidate in self._users
        ]
        return self.get(user_id)  # type: ignore[return-value]

    def set_user_borrower(
        self, user_id: int, borrower_id: int | None, *, actor: AppUser
    ) -> AppUser:
        check_manage_users(actor)
        if self.get(user_id) is None:
            raise NotFoundError("user", user_id)
        if borrower_id is not None and any(
            candidate.id != user_id and candidate.borrower_id == borrower_id
            for candidate in self._users
        ):
            raise DuplicateCodeError("borrower_id", str(borrower_id))
        self._users = [
            replace(candidate, borrower_id=borrower_id)
            if candidate.id == user_id
            else candidate
            for candidate in self._users
        ]
        return self.get(user_id)  # type: ignore[return-value]

    def set_user_staff(
        self, user_id: int, staff_id: int | None, *, actor: AppUser
    ) -> AppUser:
        check_manage_users(actor)
        if self.get(user_id) is None:
            raise NotFoundError("user", user_id)
        if staff_id is not None and any(
            candidate.id != user_id and candidate.staff_id == staff_id
            for candidate in self._users
        ):
            raise DuplicateCodeError("staff_id", str(staff_id))
        self._users = [
            replace(candidate, staff_id=staff_id)
            if candidate.id == user_id
            else candidate
            for candidate in self._users
        ]
        return self.get(user_id)  # type: ignore[return-value]

    def change_password(self, user_id: int, command: ChangePasswordCommand) -> None:
        user = self.get(user_id)
        if user is None:
            raise NotFoundError("user", user_id)
        new_hash = apply_change_password(self._passwords.get(user_id), command)
        self._passwords[user_id] = new_hash
        self._users = [
            replace(candidate, must_change_password=False)
            if candidate.id == user_id
            else candidate
            for candidate in self._users
        ]

    def admin_reset_password(
        self, user_id: int, new_password: str, *, actor: AppUser
    ) -> None:
        check_manage_users(actor)
        if self.get(user_id) is None:
            raise NotFoundError("user", user_id)
        error = validate_password_strength(new_password)
        if error is not None:
            raise ValidationError(error, field="new_password")
        self._passwords[user_id] = hash_password(new_password)
        self._users = [
            replace(candidate, must_change_password=True)
            if candidate.id == user_id
            else candidate
            for candidate in self._users
        ]

    def register_line_user(self, command: RegisterLineUser) -> AppUser:
        if self.find_by_line_sub(command.line_sub) is not None:
            raise DuplicateCodeError("line_sub", command.line_sub)
        self._next_id += 1
        user = AppUser(
            id=self._next_id,
            role=Role.USER,
            display_name=command.display_name.strip(),
            email=command.email,
            staff_id=None,
            borrower_id=None,
            status=RecordStatus.ACTIVE,
            must_change_password=False,
            last_login_at=None,
            line_sub=command.line_sub,
        )
        self._users.append(user)
        self._line_subs[user.id] = command.line_sub
        return user
