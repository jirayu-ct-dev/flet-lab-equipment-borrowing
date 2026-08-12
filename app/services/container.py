from __future__ import annotations

from dataclasses import dataclass

from .fake_services import FakeInventoryService


@dataclass
class AppServices:
    inventory_service: FakeInventoryService


def create_app_services() -> AppServices:
    return AppServices(inventory_service=FakeInventoryService())
