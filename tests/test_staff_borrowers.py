from app.services.fake_services import FakeInventoryService


def test_staff_and_borrower_service_support_lookup_and_status() -> None:
    service = FakeInventoryService()

    staff = service.create_staff("ST-999", "Ada", status="active")
    borrower = service.create_borrower("BR-999", "Lin", status="active")

    assert staff.staff_code == "ST-999"
    assert borrower.borrower_code == "BR-999"
    assert service.get_staff("ST-999").status == "active"
    assert service.get_borrower("BR-999").status == "active"
    assert service.list_staff(include_inactive=True)
    assert service.list_borrowers(include_inactive=True)
