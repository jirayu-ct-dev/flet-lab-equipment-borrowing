from app.services.fake_services import FakeInventoryService
from app.views.lost_cases import LostCasesView


def test_lost_cases_filter_and_resolve_flow() -> None:
    service = FakeInventoryService()
    view = LostCasesView(service)

    assert len(service.list_lost_cases(status="open")) == 1
    view._select_case("case-1")
    view.assessed_value.value = "12000"
    view.compensation.value = "10000"
    view.staff.value = "ST-001"
    view.reason.value = "ชดใช้ตามมูลค่าที่อนุมัติ"
    view._submit_resolution(None)

    assert service.list_lost_cases(status="open") == []
    assert service.list_lost_cases(status="resolved")[0].resolution == "compensated"
    assert view.form_container.visible is False


def test_lost_cases_form_explains_missing_fields() -> None:
    view = LostCasesView(FakeInventoryService())
    view._select_case("case-1")

    view._submit_resolution(None)

    assert view.feedback_container.content is not None
    assert "กรุณากรอก" in view.feedback_container.content.content.controls[1].value
    assert view.form_container.visible is True
