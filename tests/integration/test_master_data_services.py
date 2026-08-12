from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.contracts import (
    AcquireUnit,
    BorrowerFilter,
    CompleteRepair,
    CreateBorrower,
    CreateEquipment,
    CreateLocation,
    CreateStaff,
    EquipmentFilter,
    LocationFilter,
    RecordStatus,
    RelocateUnit,
    RetireUnit,
    StaffFilter,
    UnitFilter,
    UnitStatus,
    UpdateBorrower,
    UpdateEquipment,
    UpdateLocation,
    UpdateStaff,
    UpdateUnitNote,
)
from app.database import connect, initialize_database
from app.errors import DuplicateCodeError, InactiveRecordError, InvalidTransitionError
from app.services import (
    SQLiteBorrowerService,
    SQLiteEquipmentService,
    SQLiteLocationService,
    SQLiteStaffService,
    SQLiteUnitService,
)


@pytest.fixture
def services(tmp_path):
    database_path = tmp_path / "master-data.sqlite3"
    initialize_database(database_path)
    return {
        "path": database_path,
        "locations": SQLiteLocationService(database_path),
        "equipment": SQLiteEquipmentService(database_path),
        "staff": SQLiteStaffService(database_path),
        "borrowers": SQLiteBorrowerService(database_path),
        "units": SQLiteUnitService(database_path),
    }


def _create_references(services):
    location = services["locations"].create(CreateLocation("LAB-1", "101"))
    equipment = services["equipment"].create(
        CreateEquipment("EQ-1", "Microscope", default_location_id=location.id)
    )
    staff = services["staff"].create(CreateStaff("ST-1", "Lab Staff"))
    return location, equipment, staff


def _acquire_unit(services, asset_code="UNIT-1"):
    location, equipment, staff = _create_references(services)
    unit = services["units"].acquire(
        AcquireUnit(
            asset_code=asset_code,
            equipment_id=equipment.id,
            acquired_at=date(2026, 8, 7),
            current_location_id=location.id,
            recorded_by_staff_id=staff.id,
            reason="Initial acquisition",
            purchase_price=Decimal("1500.25"),
        )
    )
    return location, equipment, staff, unit


def test_location_crud_search_and_inactive_record(services) -> None:
    locations = services["locations"]
    created = locations.create(
        CreateLocation("LAB-A", "101", building="Science", cabinet="C1")
    )

    updated = locations.update(
        created.id,
        UpdateLocation(
            room="102",
            building="Science",
            cabinet="C2",
            shelf=None,
            status=RecordStatus.INACTIVE,
        ),
    )

    assert updated.location_code == "LAB-A"
    assert updated.room == "102"
    assert locations.get(created.id).status is RecordStatus.INACTIVE
    assert locations.search(LocationFilter(query="LAB-A")) == [updated]
    assert locations.search(LocationFilter(status=RecordStatus.ACTIVE)) == []


def test_equipment_staff_and_borrower_crud_search(services) -> None:
    location, _, staff = _create_references(services)
    equipment = services["equipment"].create(CreateEquipment("EQ-2", "Centrifuge"))
    equipment = services["equipment"].update(
        equipment.id,
        UpdateEquipment(
            name="High-speed Centrifuge",
            category="Separation",
            manufacturer=None,
            model=None,
            default_location_id=location.id,
            purchase_price=Decimal("2000"),
            status=RecordStatus.INACTIVE,
            description=None,
        ),
    )
    staff = services["staff"].update(
        staff.id,
        UpdateStaff("Former Staff", None, None, RecordStatus.INACTIVE),
    )
    borrower = services["borrowers"].create(
        CreateBorrower("BR-1", "Student One", department="Chemistry")
    )
    borrower = services["borrowers"].update(
        borrower.id,
        UpdateBorrower(
            full_name="Student One",
            department="Physics",
            email=None,
            phone=None,
            note="Graduated",
            status=RecordStatus.INACTIVE,
        ),
    )

    assert equipment.equipment_code == "EQ-2"
    assert services["equipment"].search(EquipmentFilter(query="Centrifuge")) == [
        equipment
    ]
    assert services["staff"].search(StaffFilter(status=RecordStatus.INACTIVE)) == [
        staff
    ]
    assert services["borrowers"].search(
        BorrowerFilter(status=RecordStatus.INACTIVE)
    ) == [borrower]


@pytest.mark.parametrize(
    ("service_name", "first", "duplicate", "field"),
    [
        ("locations", CreateLocation("DUP", "1"), CreateLocation("DUP", "2"), "location_code"),
        ("equipment", CreateEquipment("DUP", "A"), CreateEquipment("DUP", "B"), "equipment_code"),
        ("staff", CreateStaff("DUP", "A"), CreateStaff("DUP", "B"), "staff_code"),
        ("borrowers", CreateBorrower("DUP", "A"), CreateBorrower("DUP", "B"), "borrower_code"),
    ],
)
def test_duplicate_business_codes_are_domain_errors(
    services, service_name, first, duplicate, field
) -> None:
    service = services[service_name]
    service.create(first)

    with pytest.raises(DuplicateCodeError) as captured:
        service.create(duplicate)

    assert captured.value.field == field


def test_acquire_is_atomic_and_records_adjustment(services) -> None:
    _, _, _, unit = _acquire_unit(services)

    assert unit.status is UnitStatus.AVAILABLE
    assert unit.purchase_price == Decimal("1500.25")
    assert services["units"].search(UnitFilter(query="UNIT-1")) == [unit]

    with connect(services["path"]) as database:
        adjustment = database.execute(
            """
            SELECT action, reason FROM inventory_adjustments
            WHERE equipment_unit_id = ?
            """,
            (unit.id,),
        ).fetchone()
    assert tuple(adjustment) == ("acquire", "Initial acquisition")


def test_duplicate_asset_code_rolls_back_second_adjustment(services) -> None:
    location, equipment, staff, _ = _acquire_unit(services)

    with pytest.raises(DuplicateCodeError) as captured:
        services["units"].acquire(
            AcquireUnit(
                asset_code="UNIT-1",
                equipment_id=equipment.id,
                acquired_at=date(2026, 8, 7),
                current_location_id=location.id,
                recorded_by_staff_id=staff.id,
                reason="Duplicate",
            )
        )

    assert captured.value.field == "asset_code"
    with connect(services["path"]) as database:
        assert database.execute("SELECT COUNT(*) FROM equipment_units").fetchone()[0] == 1
        assert database.execute("SELECT COUNT(*) FROM inventory_adjustments").fetchone()[0] == 1


def test_inactive_reference_prevents_acquire_without_partial_data(services) -> None:
    location, equipment, staff = _create_references(services)
    services["staff"].update(
        staff.id,
        UpdateStaff(staff.full_name, staff.email, staff.phone, RecordStatus.INACTIVE),
    )

    with pytest.raises(InactiveRecordError):
        services["units"].acquire(
            AcquireUnit(
                asset_code="UNIT-1",
                equipment_id=equipment.id,
                acquired_at=date(2026, 8, 7),
                current_location_id=location.id,
                recorded_by_staff_id=staff.id,
                reason="Initial acquisition",
            )
        )

    assert services["units"].search() == []


def test_relocate_retire_and_update_note_create_expected_state(services) -> None:
    _, _, staff, unit = _acquire_unit(services)
    second_location = services["locations"].create(CreateLocation("LAB-2", "202"))

    relocated = services["units"].relocate(
        unit.id, RelocateUnit(second_location.id, staff.id, "Moved lab")
    )
    noted = services["units"].update_note(relocated.id, UpdateUnitNote("Calibrated"))
    retired = services["units"].retire(
        noted.id, RetireUnit(staff.id, "End of service life")
    )

    assert relocated.current_location_id == second_location.id
    assert noted.note == "Calibrated"
    assert retired.status is UnitStatus.RETIRED
    with connect(services["path"]) as database:
        actions = [
            row[0]
            for row in database.execute(
                "SELECT action FROM inventory_adjustments ORDER BY id"
            )
        ]
    assert actions == ["acquire", "relocate", "retire"]


def test_invalid_transitions_do_not_create_adjustments(services) -> None:
    _, _, staff, unit = _acquire_unit(services)

    with pytest.raises(InvalidTransitionError):
        services["units"].complete_repair(
            unit.id, CompleteRepair(unit.current_location_id, staff.id, "Not repaired")
        )

    services["units"].retire(unit.id, RetireUnit(staff.id, "Retired"))
    with pytest.raises(InvalidTransitionError):
        services["units"].retire(unit.id, RetireUnit(staff.id, "Retire twice"))

    with connect(services["path"]) as database:
        assert database.execute("SELECT COUNT(*) FROM inventory_adjustments").fetchone()[0] == 2


def test_repair_complete_only_transitions_maintenance_to_available(services) -> None:
    location, _, staff, unit = _acquire_unit(services)
    with connect(services["path"]) as database:
        database.execute(
            "UPDATE equipment_units SET status = 'maintenance' WHERE id = ?", (unit.id,)
        )
        database.commit()

    repaired = services["units"].complete_repair(
        unit.id, CompleteRepair(location.id, staff.id, "Repair passed")
    )

    assert repaired.status is UnitStatus.AVAILABLE
    assert repaired.current_location_id == location.id
