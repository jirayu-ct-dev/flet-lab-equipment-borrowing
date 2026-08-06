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

    def create_equipment(self, name: str, equipment_code: str, category: str) -> InventoryEquipment:
        equipment = InventoryEquipment(
            id=f"eq-{len(self._equipment) + 1}",
            equipment_code=equipment_code,
            name=name,
            category=category,
        )
        self._equipment.append(equipment)
        return equipment

    def create_unit(self, *, asset_code: str, equipment_id: str, location: str, status: str = "available") -> InventoryUnit:
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

    def search_units(self, keyword: str | None = None, status: str | None = None) -> list[InventoryUnit]:
        results = list(self._units)
        if keyword:
            keyword = keyword.lower()
            results = [unit for unit in results if keyword in unit.equipment_name.lower() or keyword in unit.asset_code.lower()]
        if status:
            results = [unit for unit in results if unit.status == status]
        return results
