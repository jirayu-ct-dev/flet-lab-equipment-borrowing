"""Application service implementations and frontend service container."""

from app.services.container import AppServices, create_app_services
from app.services.edits import SQLiteAuditLogService, SQLiteLoanEditService
from app.services.fake_services import FakeInventoryService
from app.services.loans import SQLiteLoanService
from app.services.lost_cases import SQLiteLostCaseService
from app.services.master_data import (
    SQLiteBorrowerService,
    SQLiteEquipmentService,
    SQLiteLocationService,
    SQLiteStaffService,
    SQLiteUnitService,
)
from app.services.queries import SQLiteLoanQueryService
from app.services.returns import SQLiteReturnService

__all__ = [
    "AppServices",
    "FakeInventoryService",
    "SQLiteAuditLogService",
    "SQLiteBorrowerService",
    "SQLiteEquipmentService",
    "SQLiteLocationService",
    "SQLiteLostCaseService",
    "SQLiteLoanEditService",
    "SQLiteLoanQueryService",
    "SQLiteLoanService",
    "SQLiteReturnService",
    "SQLiteStaffService",
    "SQLiteUnitService",
    "create_app_services",
]
