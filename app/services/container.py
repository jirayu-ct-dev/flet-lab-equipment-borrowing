from __future__ import annotations

import os
from dataclasses import dataclass

from app.database import get_database_path
from app.seed import seed_demo_data

from .sqlite_adapter import SQLiteInventoryAdapter
from .sqlite_auth_adapter import SQLiteAuthAdapter


@dataclass
class AppServices:
    inventory_service: SQLiteInventoryAdapter
    auth_service: SQLiteAuthAdapter


def create_app_services() -> AppServices:
    database_path = get_database_path()
    if os.getenv("APP_SEED_DEMO", "").strip().lower() in {"1", "true", "yes", "on"}:
        seed_demo_data(database_path)
    return AppServices(
        inventory_service=SQLiteInventoryAdapter(database_path),
        auth_service=SQLiteAuthAdapter(database_path),
    )
