from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from app.database import bangkok_today, connection, initialize_database, utc_now
from app.security import hash_password


DEMO_SEED_KEY = "general-equipment-demo-v1"
AUTH_SEED_KEY = "auth-demo-users-v2"

CATEGORIES = (
    "คอมพิวเตอร์และโน้ตบุ๊ก",
    "บอร์ดไมโครคอนโทรลเลอร์",
    "บอร์ดคอมพิวเตอร์",
    "เซ็นเซอร์ IoT",
    "กล้องและวิชัน",
    "หุ่นยนต์และโดรน",
    "เครือข่าย",
    "อุปกรณ์นำเสนอและอื่น ๆ",
    "ชิ้นส่วนซูเปอร์คอมพิวเตอร์",
)

LOCATIONS = (
    ("DEMO-LAB", "อาคารวิทยาการคอมพิวเตอร์", "ห้องปฏิบัติการ IoT", "ตู้ IOT-A", "ชั้น 2"),
    ("DEMO-COM", "อาคารวิทยาการคอมพิวเตอร์", "ห้องปฏิบัติการคอมพิวเตอร์", "ตู้ COM-A", "ชั้น 2"),
    ("DEMO-ROB", "อาคารวิทยาการคอมพิวเตอร์", "ห้องปฏิบัติการหุ่นยนต์", "ตู้ ROB-A", "ชั้น 1"),
    ("DEMO-STORE", "อาคารวิทยาการคอมพิวเตอร์", "ห้องเก็บครุภัณฑ์", "ตู้ ST-A", "ชั้น 1"),
    ("DEMO-MAINT", "อาคารวิทยาการคอมพิวเตอร์", "จุดพักซ่อม", "ตู้ซ่อม", "ชั้น 1"),
)

STAFF = (
    ("ST-DEMO-001", "กิตติพงศ์ เจ้าหน้าที่สาขา", "kittipong@example.com", "080-100-1001"),
    ("ST-DEMO-002", "พิมพ์ชนก เจ้าหน้าที่ครุภัณฑ์", "pimchanok@example.com", "080-100-1002"),
    ("ST-DEMO-003", "ณัฐวุฒิ ผู้ช่วยเจ้าหน้าที่แล็บ", "nattawut@example.com", "080-100-1003"),
)

BORROWERS = (
    ("BR-DEMO-001", "อริสา จันทร์ดี", "นักศึกษาชั้นปีที่ 3", "arisa@example.com", "081-200-2001"),
    ("BR-DEMO-002", "ธนกฤต วัฒนชัย", "อาจารย์ประจำสาขา", "thanakrit@example.com", "081-200-2002"),
    ("BR-DEMO-003", "ปวีณา สุขสวัสดิ์", "นักศึกษาชั้นปีที่ 4", "paweena@example.com", "081-200-2003"),
    ("BR-DEMO-004", "ศุภกร มีทรัพย์", "นักศึกษาชั้นปีที่ 2", "supakorn@example.com", "081-200-2004"),
    ("BR-DEMO-005", "ชลธิชา แสงทอง", "อาจารย์", "chonthicha@example.com", "081-200-2005"),
)

# Each equipment type produces two individually tracked units (25 x 2 = 50).
EQUIPMENT_TYPES = (
    ("EQ-COM-001", "โน้ตบุ๊ก Dell Latitude", "คอมพิวเตอร์และโน้ตบุ๊ก", "Dell", "Latitude 5450", "32900", "DEMO-COM", "COM-NBK"),
    ("EQ-COM-002", "จอภาพ 24 นิ้ว", "คอมพิวเตอร์และโน้ตบุ๊ก", "Samsung", "S24C310", "4590", "DEMO-COM", "COM-MON"),
    ("EQ-COM-003", "คอมพิวเตอร์ตั้งโต๊ะ", "คอมพิวเตอร์และโน้ตบุ๊ก", "HP", "ProDesk 400", "18500", "DEMO-COM", "COM-PC"),
    ("EQ-COM-004", "ชุดคีย์บอร์ดเมาส์", "คอมพิวเตอร์และโน้ตบุ๊ก", "Logitech", "MK270", "890", "DEMO-COM", "COM-KBM"),
    ("EQ-MCU-001", "Arduino Uno R4", "บอร์ดไมโครคอนโทรลเลอร์", "Arduino", "Uno R4", "1200", "DEMO-LAB", "MCU-ARD"),
    ("EQ-MCU-002", "ESP32 DevKit", "บอร์ดไมโครคอนโทรลเลอร์", "Espressif", "ESP32-WROOM", "350", "DEMO-LAB", "MCU-ESP"),
    ("EQ-MCU-003", "NodeMCU ESP8266", "บอร์ดไมโครคอนโทรลเลอร์", "Espressif", "ESP8266", "250", "DEMO-LAB", "MCU-NOD"),
    ("EQ-MCU-004", "STM32 Discovery", "บอร์ดไมโครคอนโทรลเลอร์", "STMicroelectronics", "STM32F4-Discovery", "1500", "DEMO-LAB", "MCU-STM"),
    ("EQ-MCU-005", "ชุดบอร์ด FPGA", "บอร์ดไมโครคอนโทรลเลอร์", "Terasic", "DE10-Lite", "8900", "DEMO-LAB", "MCU-FPGA"),
    ("EQ-SBC-001", "Raspberry Pi 5", "บอร์ดคอมพิวเตอร์", "Raspberry Pi", "Pi 5 8GB", "2900", "DEMO-LAB", "SBC-RPI"),
    ("EQ-SBC-002", "Raspberry Pi 4", "บอร์ดคอมพิวเตอร์", "Raspberry Pi", "Pi 4 4GB", "1800", "DEMO-LAB", "SBC-RPI4"),
    ("EQ-SBC-003", "Jetson Nano", "บอร์ดคอมพิวเตอร์", "NVIDIA", "Jetson Nano 4GB", "4500", "DEMO-ROB", "SBC-JSN"),
    ("EQ-SBC-004", "Jetson Orin Nano", "บอร์ดคอมพิวเตอร์", "NVIDIA", "Orin Nano 8GB", "14900", "DEMO-ROB", "SBC-JON"),
    ("EQ-SEN-001", "ชุดเซ็นเซอร์พื้นฐาน 37 ตัว", "เซ็นเซอร์ IoT", "DFRobot", "37-in-1 Kit", "1500", "DEMO-LAB", "SEN-BAS"),
    ("EQ-SEN-002", "เซ็นเซอร์อุณหภูมิความชื้น DHT22", "เซ็นเซอร์ IoT", "Aosong", "DHT22", "150", "DEMO-LAB", "SEN-DHT"),
    ("EQ-SEN-003", "เซ็นเซอร์ก๊าซ MQ-2", "เซ็นเซอร์ IoT", "Winsen", "MQ-2", "200", "DEMO-LAB", "SEN-GAS"),
    ("EQ-SEN-004", "โมดูล GPS", "เซ็นเซอร์ IoT", "u-blox", "NEO-6M", "450", "DEMO-LAB", "SEN-GPS"),
    ("EQ-CAM-001", "เว็บแคม 4K", "กล้องและวิชัน", "Logitech", "Brio 4K", "6900", "DEMO-COM", "CAM-WEB"),
    ("EQ-CAM-002", "กล้อง IP", "กล้องและวิชัน", "Hikvision", "DS-2CD", "5900", "DEMO-ROB", "CAM-IP"),
    ("EQ-CAM-003", "กล้อง depth RealSense", "กล้องและวิชัน", "Intel", "RealSense D435i", "16500", "DEMO-ROB", "CAM-RS"),
    ("EQ-ROB-001", "หุ่นยนต์แขนกล 6 แกน", "หุ่นยนต์และโดรน", "Dobot", "Magician", "39500", "DEMO-ROB", "ROB-ARM"),
    ("EQ-ROB-002", "โดรนถ่ายภาพ", "หุ่นยนต์และโดรน", "DJI", "Mini 4 Pro", "29900", "DEMO-ROB", "ROB-DRN"),
    ("EQ-NET-001", "สวิตช์ 10GbE", "เครือข่าย", "MikroTik", "CRS305", "5400", "DEMO-COM", "NET-SW"),
    ("EQ-NET-002", "เราเตอร์ Wi-Fi 6", "เครือข่าย", "TP-Link", "Archer AXE75", "6900", "DEMO-COM", "NET-RTR"),
    ("EQ-AV-001", "โปรเจกเตอร์", "อุปกรณ์นำเสนอและอื่น ๆ", "Epson", "EB-E01", "17900", "DEMO-STORE", "AV-PRO"),
    ("EQ-SC-001", "CPU AMD EPYC 7A53", "ชิ้นส่วนซูเปอร์คอมพิวเตอร์", "AMD", "EPYC 7A53 64C", "420000", "DEMO-STORE", "SC-CPU"),
    ("EQ-SC-002", "GPU AMD Instinct MI250X", "ชิ้นส่วนซูเปอร์คอมพิวเตอร์", "AMD", "Instinct MI250X 128GB", "2600000", "DEMO-STORE", "SC-GPU"),
    ("EQ-SC-003", "โหนด HPE Cray EX", "ชิ้นส่วนซูเปอร์คอมพิวเตอร์", "HPE", "Cray EX Frontier Node", "12000000", "DEMO-STORE", "SC-NOD"),
    ("EQ-SC-004", "สวิตช์อินเตอร์คอนเนกต์ Slingshot", "ชิ้นส่วนซูเปอร์คอมพิวเตอร์", "HPE", "Slingshot-11", "890000", "DEMO-STORE", "SC-SW"),
)

LOANS = (
    ("LOAN-DEMO-001", "BR-DEMO-001", "ST-DEMO-001", ("SBC-RPI-001", "SEN-BAS-001"), 4, 2, "ยืมทำโครงงาน IoT ระบบควบคุมโรงเพาะเห็ดอัตโนมัติ", "SEN-BAS-001", "available", "DEMO-LAB", "ชุดเซ็นเซอร์สภาพสมบูรณ์"),
    ("LOAN-DEMO-002", "BR-DEMO-002", "ST-DEMO-003", ("CAM-RS-001",), 7, -4, "ยืมกล้อง depth สอนวิชา Computer Vision", "CAM-RS-001", "available", "DEMO-ROB", "สอนเสร็จแล้ว คืนครบ"),
    ("LOAN-DEMO-003", "BR-DEMO-003", "ST-DEMO-001", ("MCU-ESP-001", "SEN-DHT-001"), 5, -1, "ยืมทำโปรเจกต์จบ ระบบรดน้ำต้นไม้อัตโนมัติ", "MCU-ESP-001", "maintenance", "DEMO-MAINT", "ช่อง USB หลวม ส่งตรวจเช็ก"),
    ("LOAN-DEMO-004", "BR-DEMO-004", "ST-DEMO-003", ("CAM-IP-001", "ROB-DRN-001"), 2, 1, "ยืมถ่ายภาพงานแข่งขันหุ่นยนต์ของสาขา", "CAM-IP-001", "reported_lost", None, "กล้องหายหลังกิจกรรมแข่งขัน"),
    ("LOAN-DEMO-005", "BR-DEMO-005", "ST-DEMO-002", ("COM-PC-001", "AV-PRO-001"), 1, 3, "ยืมคอมตั้งโต๊ะและโปรเจกเตอร์สอนในชั้นเรียน", "AV-PRO-001", "available", "DEMO-STORE", "คืนโปรเจกเตอร์แล้ว เหลือคอมที่ยังใช้งานอยู่"),
)


def _row_id(database, table: str, code_column: str, code: str) -> int:
    row = database.execute(
        f"SELECT id FROM {table} WHERE {code_column} = ?", (code,)
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Seed record not found: {table}.{code_column}={code}")
    return row["id"]


def _optional_row_id(database, table: str, code_column: str, code: str) -> int | None:
    row = database.execute(
        f"SELECT id FROM {table} WHERE {code_column} = ?", (code,)
    ).fetchone()
    return row["id"] if row is not None else None


def _seed_demo_users(database_path: str | Path | None = None) -> bool:
    """Seed demo login accounts under their own idempotency key.

    Uses a separate key so databases that were seeded before the auth system
    existed still receive the demo accounts without being wiped.
    """
    with connection(database_path) as database:
        database.execute("BEGIN IMMEDIATE")
        try:
            if database.execute(
                "SELECT 1 FROM app_seed_runs WHERE seed_key = ?", (AUTH_SEED_KEY,)
            ).fetchone():
                database.rollback()
                return False

            admin_staff_id = _optional_row_id(
                database, "staff", "staff_code", "ST-DEMO-001"
            )
            demo_borrower_id = _optional_row_id(
                database, "borrowers", "borrower_code", "BR-DEMO-001"
            )
            database.execute(
                """
                INSERT OR IGNORE INTO borrowers(
                    borrower_code, full_name, department, email, phone, note
                ) VALUES (
                    'BR-DEMO-006', 'กิตติพงศ์ เจ้าหน้าที่สาขา',
                    'เจ้าหน้าที่สาขาวิทยาการคอมพิวเตอร์',
                    'kittipong@example.com', '080-100-1001',
                    'บัญชีผู้ยืมของผู้ดูแลระบบ (ผู้ดูแลก็ยืมอุปกรณ์ได้)'
                )
                """
            )
            admin_borrower_id = _optional_row_id(
                database, "borrowers", "borrower_code", "BR-DEMO-006"
            )
            database.execute(
                """
                INSERT OR IGNORE INTO app_users(
                    role, email, password_hash, display_name, staff_id,
                    must_change_password
                ) VALUES ('admin', 'admin@lab.local', ?, 'ผู้ดูแลระบบ', ?, 1)
                """,
                (hash_password("admin123"), admin_staff_id),
            )
            database.execute(
                """
                UPDATE app_users
                SET borrower_id = ?,
                    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                WHERE email = 'admin@lab.local' AND borrower_id IS NULL
                """,
                (admin_borrower_id,),
            )
            database.execute(
                """
                INSERT OR IGNORE INTO app_users(
                    role, email, password_hash, display_name, borrower_id,
                    must_change_password
                ) VALUES ('user', 'borrower@lab.local', ?, 'ผู้ยืมทดสอบ', ?, 0)
                """,
                (hash_password("borrow123"), demo_borrower_id),
            )
            database.execute(
                "INSERT INTO app_seed_runs(seed_key) VALUES (?)", (AUTH_SEED_KEY,)
            )
            database.commit()
            return True
        except Exception:
            database.rollback()
            raise


def seed_demo_data(database_path: str | Path | None = None) -> bool:
    """Insert the Docker demo dataset once and return whether it was applied."""
    initialize_database(database_path)
    today = bangkok_today()
    now = utc_now()

    with connection(database_path) as database:
        database.execute("BEGIN IMMEDIATE")
        try:
            if database.execute(
                "SELECT 1 FROM app_seed_runs WHERE seed_key = ?", (DEMO_SEED_KEY,)
            ).fetchone():
                database.rollback()
                return _seed_demo_users(database_path)

            for name in CATEGORIES:
                database.execute(
                    "INSERT OR IGNORE INTO equipment_categories(name) VALUES (?)",
                    (name,),
                )

            for code, building, room, cabinet, shelf in LOCATIONS:
                database.execute(
                    """
                    INSERT OR IGNORE INTO locations(
                        location_code, building, room, cabinet, shelf
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (code, building, room, cabinet, shelf),
                )

            for code, name, email, phone in STAFF:
                database.execute(
                    """
                    INSERT OR IGNORE INTO staff(staff_code, full_name, email, phone)
                    VALUES (?, ?, ?, ?)
                    """,
                    (code, name, email, phone),
                )

            for code, name, department, email, phone in BORROWERS:
                database.execute(
                    """
                    INSERT OR IGNORE INTO borrowers(
                        borrower_code, full_name, department, email, phone,
                        note
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (code, name, department, email, phone, "ข้อมูลตัวอย่างสำหรับทดลองระบบ"),
                )

            admin_staff_id = _optional_row_id(
                database, "staff", "staff_code", "ST-DEMO-001"
            )
            demo_borrower_id = _optional_row_id(
                database, "borrowers", "borrower_code", "BR-DEMO-001"
            )
            system_staff_id = _row_id(
                database, "staff", "staff_code", "ST-DEMO-001"
            )
            for index, (
                equipment_code,
                name,
                category,
                manufacturer,
                model,
                price,
                location_code,
                asset_prefix,
            ) in enumerate(EQUIPMENT_TYPES, start=1):
                category_id = _row_id(
                    database, "equipment_categories", "name", category
                )
                location_id = _row_id(
                    database, "locations", "location_code", location_code
                )
                database.execute(
                    """
                    INSERT OR IGNORE INTO equipment(
                        equipment_code, name, category, manufacturer, model,
                        default_location_id, purchase_price, description,
                        category_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        equipment_code,
                        name,
                        category,
                        manufacturer,
                        model,
                        location_id,
                        price,
                        "ครุภัณฑ์ตัวอย่างสำหรับสาขาวิทยาการคอมพิวเตอร์",
                        category_id,
                    ),
                )
                equipment_id = _row_id(
                    database, "equipment", "equipment_code", equipment_code
                )
                for unit_number in (1, 2):
                    asset_code = f"{asset_prefix}-{unit_number:03d}"
                    database.execute(
                        """
                        INSERT OR IGNORE INTO equipment_units(
                            asset_code, equipment_id, serial_number,
                            current_location_id, acquired_at, purchase_price,
                            note
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            asset_code,
                            equipment_id,
                            f"DEMO-SN-{index:02d}-{unit_number:03d}",
                            location_id,
                            (today - timedelta(days=180 + index)).isoformat(),
                            price,
                            "ข้อมูลตัวอย่างพร้อมใช้งาน",
                        ),
                    )
                    unit_id = _row_id(
                        database, "equipment_units", "asset_code", asset_code
                    )
                    database.execute(
                        """
                        INSERT INTO inventory_adjustments(
                            equipment_unit_id, action, reason, staff_id
                        )
                        SELECT ?, 'acquire', 'เพิ่มจากชุดข้อมูลตัวอย่าง', ?
                        WHERE NOT EXISTS (
                            SELECT 1 FROM inventory_adjustments
                            WHERE equipment_unit_id = ? AND action = 'acquire'
                              AND reason = 'เพิ่มจากชุดข้อมูลตัวอย่าง'
                        )
                        """,
                        (unit_id, system_staff_id, unit_id),
                    )

            for loan_index, (
                transaction_code,
                borrower_code,
                staff_code,
                asset_codes,
                borrowed_days_ago,
                due_days_from_today,
                purpose,
                returned_asset_code,
                outcome,
                return_location_code,
                condition_note,
            ) in enumerate(LOANS, start=1):
                borrower_id = _row_id(
                    database, "borrowers", "borrower_code", borrower_code
                )
                staff_id = _row_id(database, "staff", "staff_code", staff_code)
                created_at = now - timedelta(days=borrowed_days_ago)
                database.execute(
                    """
                    INSERT OR IGNORE INTO borrow_transactions(
                        transaction_code, borrower_id, borrow_date, due_date,
                        purpose, recorded_by_staff_id, status, note, created_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
                    """,
                    (
                        transaction_code,
                        borrower_id,
                        (today - timedelta(days=borrowed_days_ago)).isoformat(),
                        (today + timedelta(days=due_days_from_today)).isoformat(),
                        purpose,
                        staff_id,
                        "รายการยืมตัวอย่าง",
                        created_at.isoformat(timespec="milliseconds").replace(
                            "+00:00", "Z"
                        ),
                        created_at.isoformat(timespec="milliseconds").replace(
                            "+00:00", "Z"
                        ),
                    ),
                )
                transaction_id = _row_id(
                    database,
                    "borrow_transactions",
                    "transaction_code",
                    transaction_code,
                )
                for asset_code in asset_codes:
                    unit_id = _row_id(
                        database, "equipment_units", "asset_code", asset_code
                    )
                    database.execute(
                        """
                        INSERT OR IGNORE INTO borrow_items(
                            transaction_id, equipment_unit_id
                        ) VALUES (?, ?)
                        """,
                        (transaction_id, unit_id),
                    )
                    database.execute(
                        """
                        UPDATE equipment_units
                        SET status = 'borrowed', current_location_id = NULL,
                            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        WHERE id = ?
                        """,
                        (unit_id,),
                    )

                return_time = now - timedelta(
                    days=max(borrowed_days_ago - 1, 0), hours=loan_index
                )
                database.execute(
                    """
                    INSERT INTO returns(
                        transaction_id, returned_at, received_by_staff_id, note
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        transaction_id,
                        return_time.isoformat(timespec="milliseconds").replace(
                            "+00:00", "Z"
                        ),
                        staff_id,
                        condition_note,
                    ),
                )
                return_id = database.execute(
                    "SELECT last_insert_rowid()"
                ).fetchone()[0]
                returned_unit_id = _row_id(
                    database,
                    "equipment_units",
                    "asset_code",
                    returned_asset_code,
                )
                borrow_item_id = database.execute(
                    """
                    SELECT id FROM borrow_items
                    WHERE transaction_id = ? AND equipment_unit_id = ?
                    """,
                    (transaction_id, returned_unit_id),
                ).fetchone()["id"]
                return_location_id = (
                    _row_id(
                        database,
                        "locations",
                        "location_code",
                        return_location_code,
                    )
                    if return_location_code
                    else None
                )
                database.execute(
                    """
                    INSERT INTO return_items(
                        return_id, borrow_item_id, outcome, condition_note,
                        location_id
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        return_id,
                        borrow_item_id,
                        outcome,
                        condition_note,
                        return_location_id,
                    ),
                )
                database.execute(
                    """
                    UPDATE equipment_units
                    SET status = ?, current_location_id = ?,
                        updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    WHERE id = ?
                    """,
                    (outcome, return_location_id, returned_unit_id),
                )

                if outcome == "reported_lost":
                    assessed_value = database.execute(
                        "SELECT purchase_price FROM equipment_units WHERE id = ?",
                        (returned_unit_id,),
                    ).fetchone()["purchase_price"]
                    database.execute(
                        """
                        INSERT OR IGNORE INTO lost_cases(
                            equipment_unit_id, borrow_item_id, reported_at,
                            assessed_value, note
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            returned_unit_id,
                            borrow_item_id,
                            return_time.isoformat(timespec="milliseconds").replace(
                                "+00:00", "Z"
                            ),
                            assessed_value,
                            condition_note,
                        ),
                    )

                unresolved_items = database.execute(
                    """
                    SELECT COUNT(*)
                    FROM borrow_items bi
                    LEFT JOIN return_items ri ON ri.borrow_item_id = bi.id
                    WHERE bi.transaction_id = ? AND ri.id IS NULL
                    """,
                    (transaction_id,),
                ).fetchone()[0]
                if unresolved_items == 0:
                    database.execute(
                        """
                        UPDATE borrow_transactions
                        SET status = 'completed',
                            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        WHERE id = ?
                        """,
                        (transaction_id,),
                    )

            database.execute(
                "INSERT INTO app_seed_runs(seed_key) VALUES (?)", (DEMO_SEED_KEY,)
            )
            database.commit()
            return _seed_demo_users(database_path) or True
        except Exception:
            database.rollback()
            raise
