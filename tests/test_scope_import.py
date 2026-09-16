from app.import_users import import_preview, preview_users, template_bytes
from app.service import AppService


def prepared(tmp_path):
    service = AppService(tmp_path / "app.db")
    admin = service.authenticate("admin", "admin1234")
    faculty = service.save_master(admin.id, "faculty", "วิทยาศาสตร์")
    department = service.save_master(admin.id, "department", "วิทยาการคอมพิวเตอร์", parent_id=faculty)
    cohort = service.save_master(admin.id, "cohort", "65", parent_id=department)
    service.save_master(admin.id, "class_group", "1", parent_id=cohort)
    return service, admin


def test_csv_preview_reports_duplicate_and_imports_only_valid_rows(tmp_path):
    service, admin = prepared(tmp_path)
    data = (
        "username,full_name,backup_email,role,user_type,faculty,department,cohort,class_group\n"
        "650000001,สมชาย,,borrower,student,วิทยาศาสตร์,วิทยาการคอมพิวเตอร์,65,1\n"
        "650000001,ชื่อซ้ำ,,borrower,student,วิทยาศาสตร์,วิทยาการคอมพิวเตอร์,65,1\n"
        "bad space,ชื่อผิด,,borrower,student,วิทยาศาสตร์,วิทยาการคอมพิวเตอร์,65,1\n"
    ).encode("utf-8")
    preview = preview_users(service, "users.csv", data)
    assert preview.valid_count == 1
    assert preview.error_count == 2
    created, errors = import_preview(service, admin.id, preview)
    assert created == 1
    assert errors == []
    assert service.authenticate("650000001", "650000001").full_name == "สมชาย"


def test_xlsx_template_can_be_previewed(tmp_path):
    service, _ = prepared(tmp_path)
    preview = preview_users(service, "users.xlsx", template_bytes("xlsx"))
    assert preview.valid_count == 1
    assert preview.rows[0].values["username"] == "650000001"


def test_import_accepts_faculty_name_with_or_without_prefix(tmp_path):
    service, _ = prepared(tmp_path)
    data = (
        "username,full_name,backup_email,role,user_type,faculty,department,cohort,class_group\n"
        "660112230001,นายกฤษฎา,,borrower,student,คณะวิทยาศาสตร์,วิทยาการคอมพิวเตอร์,65,1\n"
    ).encode("utf-8")

    preview = preview_users(service, "users.csv", data)

    assert preview.valid_count == 1
    assert preview.rows[0].resolved["faculty_id"] == 1


def test_import_resolves_duplicate_department_names_under_the_selected_faculty(tmp_path):
    service, admin = prepared(tmp_path)
    other_faculty = service.save_master(admin.id, "faculty", "วิศวกรรมศาสตร์")
    other_department = service.save_master(admin.id, "department", "วิทยาการคอมพิวเตอร์", parent_id=other_faculty)
    other_cohort = service.save_master(admin.id, "cohort", "65", parent_id=other_department)
    service.save_master(admin.id, "class_group", "1", parent_id=other_cohort)
    data = (
        "username,full_name,backup_email,role,user_type,faculty,department,cohort,class_group\n"
        "650000002,สมหญิง,,borrower,student,วิศวกรรมศาสตร์,วิทยาการคอมพิวเตอร์,65,1\n"
    ).encode("utf-8")
    preview = preview_users(service, "users.csv", data)
    assert preview.valid_count == 1
    assert preview.rows[0].resolved["department_id"] == other_department
