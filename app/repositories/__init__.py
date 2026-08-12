"""Persistence implementations used by domain services."""

from app.repositories.master_data import MasterDataRepository
from app.repositories.loans import LoanRepository
from app.repositories.lost_cases import LostCaseRepository
from app.repositories.returns import ReturnRepository
from app.repositories.edits import AuditLogRepository, LoanEditRepository
from app.repositories.queries import LoanQueryRepository

__all__ = [
    "AuditLogRepository",
    "LoanRepository",
    "LoanEditRepository",
    "LoanQueryRepository",
    "LostCaseRepository",
    "MasterDataRepository",
    "ReturnRepository",
]
