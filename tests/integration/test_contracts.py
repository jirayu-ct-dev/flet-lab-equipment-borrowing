from __future__ import annotations

import subprocess
import sys
from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.contracts import (
    CreateEquipment,
    CreateLocation,
    EquipmentFilter,
    Location,
    LocationFilter,
    LocationService,
    RecordStatus,
)
from app.errors import (
    DuplicateCodeError,
    ReturnAlreadyRecorded,
    UnitNotAvailable,
    ValidationError,
)


def test_contract_import_does_not_load_database_implementation() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import app.contracts; "
            "assert 'app.database' not in sys.modules",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_dtos_and_commands_are_immutable() -> None:
    location = Location(
        id=1,
        location_code="LAB-1",
        building=None,
        room="101",
        cabinet=None,
        shelf=None,
        status=RecordStatus.ACTIVE,
    )

    with pytest.raises(FrozenInstanceError):
        location.room = "102"  # type: ignore[misc]


def test_business_codes_are_not_part_of_update_commands() -> None:
    from app.contracts import UpdateEquipment, UpdateLocation

    assert "equipment_code" in CreateEquipment.__dataclass_fields__
    assert "equipment_code" not in UpdateEquipment.__dataclass_fields__
    assert "location_code" not in UpdateLocation.__dataclass_fields__


def test_service_protocol_supports_fake_implementation() -> None:
    class FakeLocationService:
        def create(self, command: CreateLocation): ...

        def get(self, location_id: int): ...

        def update(self, location_id: int, command): ...

        def search(self, filters: LocationFilter = LocationFilter()): ...

    assert isinstance(FakeLocationService(), LocationService)


def test_domain_errors_expose_stable_ui_fields() -> None:
    error = DuplicateCodeError("equipment_code", "EQ-001")

    assert error.code == "duplicate_code"
    assert error.field == "equipment_code"
    assert error.details == {"value": "EQ-001"}
    assert str(error) == error.message

    validation_error = ValidationError("Price must not be negative", field="price")
    assert validation_error.code == "validation_error"
    assert validation_error.field == "price"

    assert UnitNotAvailable(7, "borrowed").details["unit_id"] == 7
    assert ReturnAlreadyRecorded(9).code == "return_already_recorded"


def test_command_preserves_decimal_value() -> None:
    command = CreateEquipment(
        equipment_code="EQ-001",
        name="Microscope",
        purchase_price=Decimal("1250.50"),
    )

    assert command.purchase_price == Decimal("1250.50")
    assert EquipmentFilter().status is None
