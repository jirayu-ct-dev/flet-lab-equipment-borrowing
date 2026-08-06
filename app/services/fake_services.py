from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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

    def list_equipment(self) -> list[InventoryEquipment]:
        return list(self._equipment)

    def list_units(self) -> list[InventoryUnit]:
        return list(self._units)

    def get_unit(self, asset_code: str) -> InventoryUnit | None:
        for unit in self._units:
            if unit.asset_code == asset_code:
                return unit
        return None

    def search_units(self, status: str | None = None) -> list[InventoryUnit]:
        if status is None:
            return self.list_units()
        return [unit for unit in self._units if unit.status == status]
