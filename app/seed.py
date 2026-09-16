from __future__ import annotations

from pathlib import Path

from app.service import AppService


PROJECT_ROOT = Path(__file__).resolve().parent.parent

EQUIPMENT = (
    ("การ์ดจอ", "การ์ดจอ", "NVIDIA", "RTX PRO 6000", "GPU-001", "ตู้ GPU A1"),
    ("การ์ดจอ", "การ์ดจอ", "NVIDIA", "GeForce RTX 5090", "GPU-002", "ตู้ GPU A1"),
    ("การ์ดจอ", "การ์ดจอ", "NVIDIA", "GeForce RTX 5070", "GPU-003", "ตู้ GPU A1"),
    ("การ์ดจอ", "การ์ดจอ", "NVIDIA", "GeForce RTX 4080", "GPU-004", "ตู้ GPU A1"),
    ("การ์ดจอ", "การ์ดจอ", "NVIDIA", "GeForce RTX 4070 Ti SUPER", "GPU-005", "ตู้ GPU A2"),
    ("การ์ดจอ", "การ์ดจอ", "NVIDIA", "GeForce RTX 3090", "GPU-006", "ตู้ GPU A2"),
    ("การ์ดจอ", "การ์ดจอ", "NVIDIA", "GeForce RTX 3080", "GPU-007", "ตู้ GPU A2"),
    ("การ์ดจอ", "การ์ดจอ", "NVIDIA", "GeForce RTX 3070", "GPU-008", "ตู้ GPU A2"),
    ("การ์ดจอ", "การ์ดจอ", "NVIDIA", "GeForce GTX 1080 Ti", "GPU-009", "ตู้ GPU A3"),
    ("การ์ดจอ", "การ์ดจอ", "NVIDIA", "GeForce GTX 750 Ti", "GPU-010", "ตู้ GPU A3"),
    ("หน่วยประมวลผล", "ซีพียูเซิร์ฟเวอร์", "AMD", "EPYC", "CPU-001", "ตู้ CPU B1"),
    ("หน่วยประมวลผล", "ซีพียู", "AMD", "Ryzen 9 9950X3D", "CPU-002", "ตู้ CPU B1"),
    ("หน่วยประมวลผล", "ซีพียู", "AMD", "Ryzen 7 9800X3D", "CPU-003", "ตู้ CPU B1"),
    ("หน่วยประมวลผล", "ซีพียู", "Intel", "Core i9-14900K", "CPU-004", "ตู้ CPU B1"),
    ("หน่วยประมวลผล", "ซีพียู", "Intel", "Core i7-12700K", "CPU-005", "ตู้ CPU B2"),
    ("หน่วยประมวลผล", "ซีพียู", "Intel", "Core i5-14500", "CPU-006", "ตู้ CPU B2"),
    ("หน่วยประมวลผล", "ซีพียู", "Intel", "Core i5-12500", "CPU-007", "ตู้ CPU B2"),
    ("หน่วยความจำและอุปกรณ์เสริม", "หน่วยความจำ RAM", "DDR5", "32 GB", "RAM-001", "ตู้ RAM C1"),
    ("หน่วยความจำและอุปกรณ์เสริม", "หน่วยความจำ RAM", "DDR5", "64 GB", "RAM-002", "ตู้ RAM C1"),
    ("หน่วยความจำและอุปกรณ์เสริม", "หน่วยความจำ RAM", "DDR5 ECC", "128 GB", "RAM-003", "ตู้ RAM C1"),
    ("บอร์ดพัฒนาและ IoT", "บอร์ดคอมพิวเตอร์ขนาดเล็ก", "Raspberry Pi", "Raspberry Pi 5", "IOT-001", "ตู้ IoT D1"),
    ("บอร์ดพัฒนาและ IoT", "บอร์ดไมโครคอนโทรลเลอร์", "Arduino", "Arduino Uno R4", "IOT-002", "ตู้ IoT D1"),
    ("บอร์ดพัฒนาและ IoT", "บอร์ดไมโครคอนโทรลเลอร์", "Espressif", "ESP32 DevKit", "IOT-003", "ตู้ IoT D1"),
)


def seed_render_demo(service: AppService) -> bool:
    """Populate a brand-new Render SQLite database once; never overwrite data."""
    users = service.list_users()
    if len(users) != 1 or users[0]["username"].casefold() != "admin":
        return False
    actor_id = users[0]["id"]
    faculty = service.save_master(actor_id, "faculty", "คณะวิทยาศาสตร์")
    department = service.save_master(actor_id, "department", "วิทยาการคอมพิวเตอร์", parent_id=faculty)
    cohort = service.save_master(actor_id, "cohort", "66", parent_id=department)
    group = service.save_master(actor_id, "class_group", "1", parent_id=cohort)
    categories = {
        name: service.save_master(actor_id, "category", name)
        for name in ("การ์ดจอ", "หน่วยประมวลผล", "หน่วยความจำและอุปกรณ์เสริม", "บอร์ดพัฒนาและ IoT")
    }
    for line in (PROJECT_ROOT / "docs" / "cs66.md").read_text(encoding="utf-8").splitlines():
        username, full_name = line.split("\t", maxsplit=1)
        service.save_user(actor_id, username=username, full_name=full_name, faculty_id=faculty, department_id=department, cohort_id=cohort, class_group_id=group)
    for category, name, brand, model, asset_code, location in EQUIPMENT:
        equipment_type = service.save_equipment_type(actor_id, name=name, category_id=categories[category], brand=brand, model=model)
        service.save_unit(actor_id, equipment_type_id=equipment_type, asset_code=asset_code, storage_location=location)
    return True
