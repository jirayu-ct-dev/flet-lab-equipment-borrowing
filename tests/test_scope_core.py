from datetime import date, datetime, timezone

import pytest

from app.database import connect
from app.errors import AuthenticationError, ValidationError
from app.service import AppService


@pytest.fixture
def service(tmp_path):
    return AppService(tmp_path / "app.db")


def admin(service):
    return service.authenticate("ADMIN", "admin1234")


def master_data(service, actor_id):
    faculty = service.save_master(actor_id, "faculty", "วิทยาศาสตร์")
    department = service.save_master(actor_id, "department", "วิทยาการคอมพิวเตอร์", parent_id=faculty)
    cohort = service.save_master(actor_id, "cohort", "65", parent_id=department)
    group = service.save_master(actor_id, "class_group", "1", parent_id=cohort)
    category = service.save_master(actor_id, "category", "คอมพิวเตอร์")
    return faculty, department, cohort, group, category


def borrower(service, actor_id, username="650000001"):
    faculty, department, cohort, group, _ = master_data(service, actor_id)
    return service.save_user(
        actor_id,
        username=username,
        full_name="สมชาย ใจดี",
        faculty_id=faculty,
        department_id=department,
        cohort_id=cohort,
        class_group_id=group,
    )


def equipment(service, actor_id, category_id):
    equipment_type = service.save_equipment_type(actor_id, name="Notebook", category_id=category_id)
    first = service.save_unit(actor_id, equipment_type_id=equipment_type, asset_code="NB-001", storage_location="ตู้ A")
    second = service.save_unit(actor_id, equipment_type_id=equipment_type, asset_code="NB-002", storage_location="ตู้ A")
    return first, second


def test_new_database_has_one_forced_change_admin(service):
    user = admin(service)
    assert user.username == "admin"
    assert user.role == "admin"
    assert user.must_change_password is True
    with pytest.raises(AuthenticationError):
        service.authenticate("admin", "wrong")


def test_persistent_session_restores_user_and_logout_revokes_it(service):
    user = admin(service)
    token = service.create_session(user.id)
    assert service.user_for_session(token).id == user.id
    service.revoke_session(token)
    assert service.user_for_session(token) is None


def test_new_user_password_is_username_and_username_is_case_insensitive(service):
    actor = admin(service)
    user = borrower(service, actor.id, "Student.One")
    authenticated = service.authenticate("student.one", "Student.One")
    assert authenticated.id == user.id
    assert authenticated.must_change_password is True
    with pytest.raises(ValidationError, match="มีอยู่แล้ว"):
        service.save_user(actor.id, username="STUDENT.ONE", full_name="คนซ้ำ", role="admin", user_type="staff")


def test_student_requires_group_only_when_cohort_has_multiple_groups(service):
    actor = admin(service)
    faculty, department, cohort, first_group, _ = master_data(service, actor.id)
    auto = service.save_user(
        actor.id,
        username="student1",
        full_name="นักศึกษา หนึ่ง",
        faculty_id=faculty,
        department_id=department,
        cohort_id=cohort,
    )
    assert auto.class_group_id == first_group
    service.save_master(actor.id, "class_group", "2", parent_id=cohort)
    with pytest.raises(ValidationError, match="หลายหมู่เรียน"):
        service.save_user(
            actor.id,
            username="student2",
            full_name="นักศึกษา สอง",
            faculty_id=faculty,
            department_id=department,
            cohort_id=cohort,
        )


def test_loan_is_atomic_and_partial_return_updates_each_unit(service):
    actor = admin(service)
    faculty, department, cohort, group, category = master_data(service, actor.id)
    user = service.save_user(
        actor.id,
        username="student1",
        full_name="นักศึกษา",
        faculty_id=faculty,
        department_id=department,
        cohort_id=cohort,
        class_group_id=group,
    )
    first, second = equipment(service, actor.id, category)
    loan = service.create_loan(actor.id, user.id, [first, second], date(2026, 9, 14), date(2026, 9, 20))
    items = service.loan_items(loan["id"])
    service.return_items(actor.id, loan["id"], [items[0]["id"]], datetime(2026, 9, 15, tzinfo=timezone.utc))
    assert [row["status"] for row in service.list_units()] == ["available", "borrowed"]
    assert service.list_loans(status="active")[0]["outstanding_count"] == 1
    service.return_items(actor.id, loan["id"], [items[1]["id"]])
    assert service.list_loans(status="completed")[0]["outstanding_count"] == 0

    third = service.save_unit(actor.id, equipment_type_id=service.list_equipment_types()[0]["id"], asset_code="NB-003", storage_location="ตู้ A")
    with pytest.raises(ValidationError, match="ไม่พร้อมยืม"):
        service.create_loan(actor.id, user.id, [third, 9999], date(2026, 9, 21), date(2026, 9, 22))
    assert next(row for row in service.list_units() if row["id"] == third)["status"] == "available"


def test_overdue_user_cannot_borrow_more(service, monkeypatch):
    actor = admin(service)
    faculty, department, cohort, group, category = master_data(service, actor.id)
    user = service.save_user(actor.id, username="student1", full_name="นักศึกษา", faculty_id=faculty, department_id=department, cohort_id=cohort, class_group_id=group)
    first, second = equipment(service, actor.id, category)
    monkeypatch.setattr("app.service.bangkok_today", lambda: date(2026, 9, 20))
    service.create_loan(actor.id, user.id, [first], date(2026, 9, 1), date(2026, 9, 10))
    with pytest.raises(ValidationError, match="เกินกำหนด"):
        service.create_loan(actor.id, user.id, [second], date(2026, 9, 20), date(2026, 9, 21))


def test_line_link_is_one_to_one_and_can_be_removed(service):
    actor = admin(service)
    first = borrower(service, actor.id, "student1")
    linked = service.link_line("student1", "student1", "U123")
    assert linked.id == first.id
    assert service.find_by_line("U123").id == first.id
    service.save_user(actor.id, username="student2", full_name="ผู้ดูแลย่อย", role="admin", user_type="staff")
    with pytest.raises(ValidationError, match="ผูกกับผู้ใช้อื่น"):
        service.link_line("student2", "student2", "U123")
    service.unlink_line(first.id)
    assert service.find_by_line("U123") is None


def test_reminders_are_claimed_once_at_three_and_one_days(service):
    actor = admin(service)
    faculty, department, cohort, group, category = master_data(service, actor.id)
    user = service.save_user(actor.id, username="student1", full_name="นักศึกษา", faculty_id=faculty, department_id=department, cohort_id=cohort, class_group_id=group)
    service.link_line("student1", "student1", "U123")
    unit, _ = equipment(service, actor.id, category)
    service.create_loan(actor.id, user.id, [unit], date(2026, 9, 10), date(2026, 9, 20))
    assert len(service.claim_due_reminders(date(2026, 9, 17))) == 1
    assert service.claim_due_reminders(date(2026, 9, 17)) == []
    assert len(service.claim_due_reminders(date(2026, 9, 19))) == 1


def test_scope_schema_contains_no_removed_features(service):
    with connect(service.path) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"users", "loans", "loan_items", "equipment_units"} <= tables
    assert {"audit_logs", "lost_cases", "lost_reports", "returns", "return_items"}.isdisjoint(tables)


def test_inactive_equipment_type_is_not_offered_as_available(service):
    actor = admin(service)
    _, _, _, _, category = master_data(service, actor.id)
    unit, _ = equipment(service, actor.id, category)
    equipment_type_id = next(row for row in service.list_units() if row["id"] == unit)["equipment_type_id"]
    service.set_equipment_type_status(actor.id, equipment_type_id, "inactive")
    assert service.list_units(status="available") == []


def test_unit_search_includes_brand_and_model(service):
    actor = admin(service)
    _, _, _, _, category = master_data(service, actor.id)
    equipment_type = service.save_equipment_type(actor.id, name="การ์ดจอ", category_id=category, brand="NVIDIA", model="RTX 5090")
    service.save_unit(actor.id, equipment_type_id=equipment_type, asset_code="GPU-001", storage_location="ห้องแล็บ")

    assert [row["asset_code"] for row in service.list_units("NVIDIA", "available")] == ["GPU-001"]
    assert [row["asset_code"] for row in service.list_units("5090", "available")] == ["GPU-001"]


def test_returned_today_uses_bangkok_calendar_date(service, monkeypatch):
    actor = admin(service)
    faculty, department, cohort, group, category = master_data(service, actor.id)
    user = service.save_user(actor.id, username="student1", full_name="นักศึกษา", faculty_id=faculty, department_id=department, cohort_id=cohort, class_group_id=group)
    unit, _ = equipment(service, actor.id, category)
    loan = service.create_loan(actor.id, user.id, [unit], date(2026, 9, 13), date(2026, 9, 20))
    item = service.loan_items(loan["id"])[0]
    service.return_items(actor.id, loan["id"], [item["id"]], datetime(2026, 9, 13, 18, tzinfo=timezone.utc))
    monkeypatch.setattr("app.service.bangkok_today", lambda: date(2026, 9, 14))
    assert service.dashboard(actor)["returned_today"] == 1


def test_child_master_data_requires_an_active_parent(service):
    actor = admin(service)
    faculty = service.save_master(actor.id, "faculty", "วิทยาศาสตร์")
    service.set_master_status(actor.id, "faculty", faculty, "inactive")
    with pytest.raises(ValidationError, match="ข้อมูลแม่"):
        service.save_master(actor.id, "department", "วิทยาการคอมพิวเตอร์", parent_id=faculty)
