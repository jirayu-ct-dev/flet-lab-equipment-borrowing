from __future__ import annotations

from dataclasses import dataclass

from app.database import get_database_path

from .sqlite_adapter import SQLiteInventoryAdapter


@dataclass
class AppServices:
    inventory_service: SQLiteInventoryAdapter


def create_app_services() -> AppServices:
    return AppServices(inventory_service=SQLiteInventoryAdapter(get_database_path()))
