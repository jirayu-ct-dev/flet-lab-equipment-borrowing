from app.services.container import create_app_services
from app.services.fake_services import FakeInventoryService


def test_fake_inventory_service_contains_seeded_fixtures() -> None:
    service = FakeInventoryService()
    units = service.list_units()

    assert len(units) >= 5
    statuses = {unit.status for unit in units}
    assert {"available", "borrowed", "maintenance", "reported_lost", "retired"} <= statuses


def test_container_returns_fake_services_by_default() -> None:
    services = create_app_services()

    assert services.inventory_service is not None
    assert services.inventory_service.list_units()
