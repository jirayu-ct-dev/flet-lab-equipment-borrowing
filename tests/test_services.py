from app.services.container import create_app_services
from app.services.fake_services import FakeInventoryService
from app.services.sqlite_adapter import SQLiteInventoryAdapter


def test_fake_inventory_service_contains_seeded_fixtures() -> None:
    service = FakeInventoryService()
    units = service.list_units()

    assert len(units) >= 5
    statuses = {unit.status for unit in units}
    assert {"available", "borrowed", "maintenance", "reported_lost", "retired"} <= statuses


def test_container_returns_sqlite_services_by_default(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("APP_DB_PATH", str(tmp_path / "app.db"))
    monkeypatch.delenv("APP_SEED_DEMO", raising=False)
    services = create_app_services()

    assert isinstance(services.inventory_service, SQLiteInventoryAdapter)
    assert services.inventory_service.list_units() == []


def test_container_seeds_demo_data_when_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("APP_DB_PATH", str(tmp_path / "seeded.db"))
    monkeypatch.setenv("APP_SEED_DEMO", "1")

    services = create_app_services()

    assert len(services.inventory_service.list_units()) == 58
    assert len(services.inventory_service.list_borrowers()) == 6
    assert len(services.inventory_service.list_loans()) == 5
