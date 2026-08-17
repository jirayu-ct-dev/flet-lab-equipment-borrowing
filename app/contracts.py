from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol, runtime_checkable


class RecordStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class UnitStatus(StrEnum):
    AVAILABLE = "available"
    BORROWED = "borrowed"
    MAINTENANCE = "maintenance"
    REPORTED_LOST = "reported_lost"
    RETIRED = "retired"


class LoanStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReturnOutcome(StrEnum):
    AVAILABLE = "available"
    MAINTENANCE = "maintenance"
    REPORTED_LOST = "reported_lost"


class LostResolution(StrEnum):
    RECOVERED = "recovered"
    REPLACED = "replaced"
    COMPENSATED = "compensated"
    WAIVED = "waived"


class LostReportStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LoanQueryState(StrEnum):
    ACTIVE = "active"
    PARTIAL = "partial"
    DUE_TODAY = "due_today"
    DUE_SOON = "due_soon"
    OVERDUE = "overdue"


@dataclass(frozen=True, slots=True)
class Location:
    id: int
    location_code: str
    building: str | None
    room: str
    cabinet: str | None
    shelf: str | None
    status: RecordStatus


@dataclass(frozen=True, slots=True)
class Equipment:
    id: int
    equipment_code: str
    name: str
    category: str | None
    manufacturer: str | None
    model: str | None
    default_location_id: int | None
    purchase_price: Decimal | None
    status: RecordStatus
    description: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class EquipmentUnit:
    id: int
    asset_code: str
    equipment_id: int
    serial_number: str | None
    current_location_id: int | None
    status: UnitStatus
    acquired_at: date
    purchase_price: Decimal | None
    note: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Staff:
    id: int
    staff_code: str
    full_name: str
    email: str | None
    phone: str | None
    status: RecordStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Borrower:
    id: int
    borrower_code: str
    full_name: str
    department: str | None
    email: str | None
    phone: str | None
    note: str | None
    status: RecordStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class LoanItem:
    id: int
    equipment_unit_id: int
    asset_code: str
    unit_status: UnitStatus


@dataclass(frozen=True, slots=True)
class Loan:
    id: int
    transaction_code: str
    borrower_id: int
    borrow_date: date
    due_date: date
    purpose: str | None
    recorded_by_staff_id: int
    status: LoanStatus
    note: str | None
    items: tuple[LoanItem, ...]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ReturnItem:
    id: int
    borrow_item_id: int
    equipment_unit_id: int
    asset_code: str
    outcome: ReturnOutcome
    location_id: int | None
    condition_note: str | None


@dataclass(frozen=True, slots=True)
class ReturnEvent:
    id: int
    loan_id: int
    returned_at: datetime
    received_by_staff_id: int
    note: str | None
    items: tuple[ReturnItem, ...]


@dataclass(frozen=True, slots=True)
class LostCase:
    id: int
    equipment_unit_id: int
    borrow_item_id: int
    reported_at: datetime
    assessed_value: Decimal | None
    approved_compensation: Decimal | None
    resolution: LostResolution | None
    approved_by_staff_id: int | None
    resolved_at: datetime | None
    replacement_unit_id: int | None
    note: str | None


@dataclass(frozen=True, slots=True)
class LostReport:
    id: int
    borrower_id: int
    equipment_unit_id: int
    reported_at: datetime
    lost_date: str | None
    location: str | None
    description: str | None
    status: LostReportStatus
    reviewed_by_staff_id: int | None
    reviewed_at: datetime | None
    review_note: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AuditLog:
    id: int
    entity_type: str
    entity_id: int
    action: str
    before: dict[str, object] | None
    after: dict[str, object] | None
    reason: str
    staff_id: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class LoanSummary:
    id: int
    transaction_code: str
    borrower_id: int
    borrower_code: str
    borrower_name: str
    borrow_date: date
    due_date: date
    status: LoanStatus
    item_count: int
    resolved_item_count: int
    outstanding_item_count: int
    states: tuple[LoanQueryState, ...]


@dataclass(frozen=True, slots=True)
class CreateLocation:
    location_code: str
    room: str
    building: str | None = None
    cabinet: str | None = None
    shelf: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateLocation:
    room: str
    building: str | None
    cabinet: str | None
    shelf: str | None
    status: RecordStatus


@dataclass(frozen=True, slots=True)
class LocationFilter:
    query: str | None = None
    status: RecordStatus | None = None


@dataclass(frozen=True, slots=True)
class CreateEquipment:
    equipment_code: str
    name: str
    category: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    default_location_id: int | None = None
    purchase_price: Decimal | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateEquipment:
    name: str
    category: str | None
    manufacturer: str | None
    model: str | None
    default_location_id: int | None
    purchase_price: Decimal | None
    status: RecordStatus
    description: str | None


@dataclass(frozen=True, slots=True)
class EquipmentFilter:
    query: str | None = None
    status: RecordStatus | None = None


@dataclass(frozen=True, slots=True)
class AcquireUnit:
    asset_code: str
    equipment_id: int
    acquired_at: date
    current_location_id: int
    recorded_by_staff_id: int
    reason: str
    serial_number: str | None = None
    purchase_price: Decimal | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateUnitNote:
    note: str | None


@dataclass(frozen=True, slots=True)
class RelocateUnit:
    location_id: int
    recorded_by_staff_id: int
    reason: str


@dataclass(frozen=True, slots=True)
class RetireUnit:
    recorded_by_staff_id: int
    reason: str


@dataclass(frozen=True, slots=True)
class CompleteRepair:
    location_id: int
    recorded_by_staff_id: int
    reason: str


@dataclass(frozen=True, slots=True)
class UnitFilter:
    query: str | None = None
    equipment_id: int | None = None
    location_id: int | None = None
    status: UnitStatus | None = None
    category: str | None = None


@dataclass(frozen=True, slots=True)
class CreateStaff:
    staff_code: str
    full_name: str
    email: str | None = None
    phone: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateStaff:
    full_name: str
    email: str | None
    phone: str | None
    status: RecordStatus


@dataclass(frozen=True, slots=True)
class StaffFilter:
    query: str | None = None
    status: RecordStatus | None = None


@dataclass(frozen=True, slots=True)
class CreateBorrower:
    borrower_code: str
    full_name: str
    department: str | None = None
    email: str | None = None
    phone: str | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateBorrower:
    full_name: str
    department: str | None
    email: str | None
    phone: str | None
    note: str | None
    status: RecordStatus


@dataclass(frozen=True, slots=True)
class BorrowerFilter:
    query: str | None = None
    status: RecordStatus | None = None


@dataclass(frozen=True, slots=True)
class CreateDraftLoan:
    transaction_code: str
    borrower_id: int
    recorded_by_staff_id: int
    borrow_date: date
    due_date: date
    unit_ids: tuple[int, ...]
    purpose: str | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class ReturnItemCommand:
    borrow_item_id: int
    outcome: ReturnOutcome
    location_id: int | None = None
    condition_note: str | None = None


@dataclass(frozen=True, slots=True)
class RecordReturn:
    loan_id: int
    returned_at: datetime
    received_by_staff_id: int
    items: tuple[ReturnItemCommand, ...]
    note: str | None = None


@dataclass(frozen=True, slots=True)
class ReplacementUnit:
    asset_code: str
    acquired_at: date
    location_id: int
    serial_number: str | None = None
    purchase_price: Decimal | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class ResolveLostCase:
    resolution: LostResolution
    assessed_value: Decimal | None
    approved_compensation: Decimal | None
    approved_by_staff_id: int | None
    reason: str
    note: str | None = None
    recovered_outcome: ReturnOutcome | None = None
    location_id: int | None = None
    replacement: ReplacementUnit | None = None


@dataclass(frozen=True, slots=True)
class CreateLostReport:
    borrower_id: int
    equipment_unit_id: int
    lost_date: str | None = None
    location: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class ReviewLostReport:
    approved: bool
    reviewed_by_staff_id: int
    review_note: str | None = None


@dataclass(frozen=True, slots=True)
class EditLoanDetails:
    due_date: date
    purpose: str | None
    note: str | None
    reason: str
    performed_by_staff_id: int


@dataclass(frozen=True, slots=True)
class ChangeLoanBorrower:
    borrower_id: int
    reason: str
    performed_by_staff_id: int


@dataclass(frozen=True, slots=True)
class ReplaceLoanUnit:
    borrow_item_id: int
    new_unit_id: int
    returned_location_id: int
    reason: str
    performed_by_staff_id: int


@dataclass(frozen=True, slots=True)
class LoanQueryFilter:
    state: LoanQueryState | None = None
    borrower_query: str | None = None
    equipment_query: str | None = None
    asset_code: str | None = None
    borrow_date_from: date | None = None
    borrow_date_to: date | None = None


@runtime_checkable
class LocationService(Protocol):
    def create(self, command: CreateLocation) -> Location: ...

    def get(self, location_id: int) -> Location: ...

    def update(self, location_id: int, command: UpdateLocation) -> Location: ...

    def search(self, filters: LocationFilter = LocationFilter()) -> list[Location]: ...


@runtime_checkable
class EquipmentService(Protocol):
    def create(self, command: CreateEquipment) -> Equipment: ...

    def get(self, equipment_id: int) -> Equipment: ...

    def update(self, equipment_id: int, command: UpdateEquipment) -> Equipment: ...

    def search(self, filters: EquipmentFilter = EquipmentFilter()) -> list[Equipment]: ...


@runtime_checkable
class UnitService(Protocol):
    def acquire(self, command: AcquireUnit) -> EquipmentUnit: ...

    def get(self, unit_id: int) -> EquipmentUnit: ...

    def update_note(self, unit_id: int, command: UpdateUnitNote) -> EquipmentUnit: ...

    def relocate(self, unit_id: int, command: RelocateUnit) -> EquipmentUnit: ...

    def retire(self, unit_id: int, command: RetireUnit) -> EquipmentUnit: ...

    def complete_repair(
        self, unit_id: int, command: CompleteRepair
    ) -> EquipmentUnit: ...

    def search(self, filters: UnitFilter = UnitFilter()) -> list[EquipmentUnit]: ...


@runtime_checkable
class StaffService(Protocol):
    def create(self, command: CreateStaff) -> Staff: ...

    def get(self, staff_id: int) -> Staff: ...

    def update(self, staff_id: int, command: UpdateStaff) -> Staff: ...

    def search(self, filters: StaffFilter = StaffFilter()) -> list[Staff]: ...


@runtime_checkable
class BorrowerService(Protocol):
    def create(self, command: CreateBorrower) -> Borrower: ...

    def get(self, borrower_id: int) -> Borrower: ...

    def update(self, borrower_id: int, command: UpdateBorrower) -> Borrower: ...

    def search(self, filters: BorrowerFilter = BorrowerFilter()) -> list[Borrower]: ...


@runtime_checkable
class LoanService(Protocol):
    def create_draft(self, command: CreateDraftLoan) -> Loan: ...

    def create_and_confirm(self, command: CreateDraftLoan) -> Loan: ...

    def get(self, loan_id: int) -> Loan: ...

    def confirm_loan(self, loan_id: int) -> Loan: ...


@runtime_checkable
class ReturnService(Protocol):
    def record_return(self, command: RecordReturn) -> ReturnEvent: ...

    def list_for_loan(self, loan_id: int) -> list[ReturnEvent]: ...


@runtime_checkable
class LostCaseService(Protocol):
    def get(self, case_id: int) -> LostCase: ...

    def resolve_lost_case(
        self, case_id: int, command: ResolveLostCase
    ) -> LostCase: ...


@runtime_checkable
class LostReportService(Protocol):
    def create_report(self, command: CreateLostReport) -> LostReport: ...

    def list_pending_reports(self) -> list[LostReport]: ...

    def list_reports_for_borrower(self, borrower_id: int) -> list[LostReport]: ...

    def review_report(self, report_id: int, command: ReviewLostReport) -> LostReport: ...


@runtime_checkable
class LoanEditService(Protocol):
    def edit_details(self, loan_id: int, command: EditLoanDetails) -> Loan: ...

    def change_borrower(
        self, loan_id: int, command: ChangeLoanBorrower
    ) -> Loan: ...

    def replace_unit(self, loan_id: int, command: ReplaceLoanUnit) -> Loan: ...


@runtime_checkable
class AuditLogService(Protocol):
    def list_for_entity(self, entity_type: str, entity_id: int) -> list[AuditLog]: ...


@runtime_checkable
class LoanQueryService(Protocol):
    def search(self, filters: LoanQueryFilter = LoanQueryFilter()) -> list[LoanSummary]: ...


class Role(StrEnum):
    ADMIN = "admin"
    USER = "user"


class Permission(StrEnum):
    VIEW_DASHBOARD = "view_dashboard"
    VIEW_INVENTORY = "view_inventory"
    VIEW_HISTORY = "view_history"
    VIEW_MY_LOANS = "view_my_loans"
    MANAGE_LOANS = "manage_loans"
    MANAGE_INVENTORY = "manage_inventory"
    MANAGE_PEOPLE = "manage_people"
    MANAGE_USERS = "manage_users"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(Permission),
    Role.USER: frozenset({
        Permission.VIEW_INVENTORY,
        Permission.VIEW_HISTORY,
        Permission.VIEW_MY_LOANS,
    }),
}


def has_permission(user: "AppUser | None", permission: Permission) -> bool:
    """False for None (unauthenticated)."""
    if user is None:
        return False
    return permission in ROLE_PERMISSIONS[user.role]


@dataclass(frozen=True, slots=True)
class AppUser:
    id: int
    role: Role
    display_name: str
    email: str | None
    staff_id: int | None
    borrower_id: int | None
    status: RecordStatus
    must_change_password: bool
    last_login_at: datetime | None
    line_sub: str | None = None


@dataclass(frozen=True, slots=True)
class LoginCommand:
    identity: str          # email
    password: str


@dataclass(frozen=True, slots=True)
class CreateUserCommand:
    role: Role
    display_name: str
    email: str | None = None
    password: str | None = None
    staff_id: int | None = None
    borrower_id: int | None = None


@dataclass(frozen=True, slots=True)
class ChangePasswordCommand:
    current_password: str
    new_password: str


@dataclass(frozen=True, slots=True)
class RegisterLineUser:
    line_sub: str
    display_name: str
    email: str | None = None
    borrower_code: str | None = None
    department: str | None = None


@runtime_checkable
class AuthService(Protocol):
    def authenticate(self, command: LoginCommand) -> AppUser: ...

    def get(self, user_id: int) -> AppUser | None: ...

    def find_by_line_sub(self, line_sub: str) -> AppUser | None: ...

    def list_users(self) -> list[AppUser]: ...

    def create_user(self, command: CreateUserCommand, *, actor: AppUser) -> AppUser: ...

    def set_user_status(self, user_id: int, status: RecordStatus, *, actor: AppUser) -> None: ...

    def set_user_role(self, user_id: int, new_role: Role, *, actor: AppUser) -> AppUser: ...

    def set_user_borrower(
        self, user_id: int, borrower_id: int | None, *, actor: AppUser
    ) -> AppUser: ...

    def change_password(self, user_id: int, command: ChangePasswordCommand) -> None: ...

    def admin_reset_password(self, user_id: int, new_password: str, *, actor: AppUser) -> None: ...

    def register_line_user(self, command: RegisterLineUser) -> AppUser: ...
