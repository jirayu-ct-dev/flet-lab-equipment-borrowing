from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class DomainError(Exception):
    """Base error carrying stable, UI-friendly error information."""

    code = "domain_error"

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.field = field
        self.details = dict(details or {})


class ValidationError(DomainError):
    code = "validation_error"


class NotFoundError(DomainError):
    code = "not_found"

    def __init__(self, entity: str, entity_id: int) -> None:
        super().__init__(
            f"{entity} with id {entity_id} was not found",
            details={"entity": entity, "entity_id": entity_id},
        )


class DuplicateCodeError(DomainError):
    code = "duplicate_code"

    def __init__(self, field: str, value: str) -> None:
        super().__init__(
            f"{field} '{value}' is already in use",
            field=field,
            details={"value": value},
        )


class InvalidTransitionError(DomainError):
    code = "invalid_transition"

    def __init__(self, current_status: str, target_status: str) -> None:
        super().__init__(
            f"Cannot change status from {current_status} to {target_status}",
            field="status",
            details={
                "current_status": current_status,
                "target_status": target_status,
            },
        )


class InactiveRecordError(DomainError):
    code = "inactive_record"

    def __init__(self, entity: str, entity_id: int) -> None:
        super().__init__(
            f"{entity} with id {entity_id} is inactive",
            details={"entity": entity, "entity_id": entity_id},
        )


class UnitNotAvailable(DomainError):
    code = "unit_not_available"

    def __init__(self, unit_id: int, current_status: str) -> None:
        super().__init__(
            f"Equipment unit {unit_id} is not available",
            details={"unit_id": unit_id, "current_status": current_status},
        )


class ReturnAlreadyRecorded(DomainError):
    code = "return_already_recorded"

    def __init__(self, borrow_item_id: int) -> None:
        super().__init__(
            f"A return has already been recorded for borrow item {borrow_item_id}",
            details={"borrow_item_id": borrow_item_id},
        )


class LoanNotDraft(DomainError):
    code = "loan_not_draft"

    def __init__(self, loan_id: int, current_status: str) -> None:
        super().__init__(
            f"Loan {loan_id} is not a draft",
            details={"loan_id": loan_id, "current_status": current_status},
        )


class LoanNotActive(DomainError):
    code = "loan_not_active"

    def __init__(self, loan_id: int, current_status: str) -> None:
        super().__init__(
            f"Loan {loan_id} is not active",
            details={"loan_id": loan_id, "current_status": current_status},
        )


class BorrowItemNotInLoan(DomainError):
    code = "borrow_item_not_in_loan"

    def __init__(self, borrow_item_id: int, loan_id: int) -> None:
        super().__init__(
            f"Borrow item {borrow_item_id} does not belong to loan {loan_id}",
            field="items",
            details={"borrow_item_id": borrow_item_id, "loan_id": loan_id},
        )


class LostCaseAlreadyResolved(DomainError):
    code = "lost_case_already_resolved"

    def __init__(self, case_id: int, resolution: str) -> None:
        super().__init__(
            f"Lost case {case_id} has already been resolved",
            details={"case_id": case_id, "resolution": resolution},
        )
