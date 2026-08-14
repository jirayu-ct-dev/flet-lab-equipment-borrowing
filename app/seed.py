from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from app.database import bangkok_today, connection, initialize_database, utc_now


DEMO_SEED_KEY = "general-equipment-demo-v1"

CATEGORIES = (
    "คอมพิวเตอร์และไอที",
    "เครื่องมือวิทยาศาสตร์",
    "โสตทัศนูปกรณ์",
    "เครื่องมือช่าง",
    "อุปกรณ์สำนักงาน",
    "อุปกรณ์กิจกรรม",
    "อุปกรณ์ความปลอดภัย",
    "อื่น ๆ",
)

LOCATIONS = (
    ("DEMO-IT", "ศูนย์อุปกรณ์", "โซนอุปกรณ์ไอที", "ตู้ IT-A", "ชั้น 1"),
    ("DEMO-SCI", "ศูนย์อุปกรณ์", "โซนเครื่องมือวิทยาศาสตร์", "ตู้ SCI-A", "ชั้น 1"),
    ("DEMO-AV", "ศูนย์อุปกรณ์", "โซนสื่อและกิจกรรม", "ตู้ AV-A", "ชั้น 2"),
    ("DEMO-GEN", "ศูนย์อุปกรณ์", "คลังอุปกรณ์ทั่วไป", "ตู้ GEN-A", "ชั้น 1"),
    ("DEMO-MAINT", "อาคารบริการ", "จุดพักซ่อม", "ตู้ซ่อม", "ชั้น 1"),
)

STAFF = (
    ("ST-DEMO-001", "กิตติพงศ์ ผู้ดูแลอุปกรณ์", "kittipong@example.com", "080-100-1001"),
    ("ST-DEMO-002", "พิมพ์ชนก เจ้าหน้าที่พัสดุ", "pimchanok@example.com", "080-100-1002"),
    ("ST-DEMO-003", "ณัฐวุฒิ ผู้ประสานงาน", "nattawut@example.com", "080-100-1003"),
)

BORROWERS = (
    ("BR-DEMO-001", "อริสา จันทร์ดี", "ฝ่ายเทคโนโลยีสารสนเทศ", "arisa@example.com", "081-200-2001"),
    ("BR-DEMO-002", "ธนกฤต วัฒนชัย", "งานวิจัยและพัฒนา", "thanakrit@example.com", "081-200-2002"),
    ("BR-DEMO-003", "ปวีณา สุขสวัสดิ์", "ฝ่ายปฏิบัติการ", "paweena@example.com", "081-200-2003"),
    ("BR-DEMO-004", "ศุภกร มีทรัพย์", "งานอาคารสถานที่", "supakorn@example.com", "081-200-2004"),
    ("BR-DEMO-005", "ชลธิชา แสงทอง", "ฝ่ายสื่อสารองค์กร", "chonthicha@example.com", "081-200-2005"),
)

# Each equipment type produces two individually tracked units (25 x 2 = 50).
EQUIPMENT_TYPES = (
    ("EQ-IT-001", "โน้ตบุ๊ก Dell Latitude", "คอมพิวเตอร์และไอที", "Dell", "Latitude 5450", "32900", "DEMO-IT", "IT-NBK"),
    ("EQ-IT-002", "โน้ตบุ๊ก Lenovo ThinkPad", "คอมพิวเตอร์และไอที", "Lenovo", "ThinkPad E14", "31500", "DEMO-IT", "IT-NBL"),
    ("EQ-IT-003", "จอภาพ 24 นิ้ว", "คอมพิวเตอร์และไอที", "Samsung", "S24C310", "4590", "DEMO-IT", "IT-MON"),
    ("EQ-IT-004", "คีย์บอร์ดไร้สาย", "คอมพิวเตอร์และไอที", "Logitech", "K380", "1290", "DEMO-IT", "IT-KBD"),
    ("EQ-IT-005", "เมาส์ไร้สาย", "คอมพิวเตอร์และไอที", "Logitech", "M331", "690", "DEMO-IT", "IT-MSE"),
    ("EQ-IT-006", "เราเตอร์ Wi-Fi", "คอมพิวเตอร์และไอที", "TP-Link", "Archer AX23", "2490", "DEMO-IT", "IT-RTR"),
    ("EQ-IT-007", "External SSD 1 TB", "คอมพิวเตอร์และไอที", "SanDisk", "Extreme Portable", "3990", "DEMO-IT", "IT-SSD"),
    ("EQ-IT-008", "กล้องเว็บแคม", "คอมพิวเตอร์และไอที", "Logitech", "C920", "2890", "DEMO-IT", "IT-WEB"),
    ("EQ-OFF-001", "เครื่องพิมพ์ฉลาก", "อุปกรณ์สำนักงาน", "Brother", "PT-D210", "1890", "DEMO-GEN", "OFF-PRN"),
    ("EQ-IT-009", "แท็บเล็ต", "คอมพิวเตอร์และไอที", "Samsung", "Galaxy Tab A9", "7990", "DEMO-IT", "IT-TAB"),
    ("EQ-SCI-001", "กล้องจุลทรรศน์", "เครื่องมือวิทยาศาสตร์", "Olympus", "CX23", "42500", "DEMO-SCI", "SCI-MIC"),
    ("EQ-SCI-002", "เครื่องชั่งดิจิทัล", "เครื่องมือวิทยาศาสตร์", "Ohaus", "Scout SPX", "18500", "DEMO-SCI", "SCI-BAL"),
    ("EQ-SCI-003", "เครื่องวัดค่า pH", "เครื่องมือวิทยาศาสตร์", "Hanna", "HI98107", "5900", "DEMO-SCI", "SCI-PHM"),
    ("EQ-SCI-004", "เครื่องวัดอุณหภูมิ", "เครื่องมือวิทยาศาสตร์", "Testo", "Testo 110", "7200", "DEMO-SCI", "SCI-TMP"),
    ("EQ-SCI-005", "เครื่องกวนสารแม่เหล็ก", "เครื่องมือวิทยาศาสตร์", "IKA", "C-MAG HS 4", "14900", "DEMO-SCI", "SCI-STR"),
    ("EQ-SCI-006", "เครื่องวัดความชื้น", "เครื่องมือวิทยาศาสตร์", "Benetech", "GM1362", "2490", "DEMO-SCI", "SCI-HUM"),
    ("EQ-SCI-007", "ชุดทดลองไฟฟ้า", "เครื่องมือวิทยาศาสตร์", "Pasco", "Basic Electricity", "8900", "DEMO-SCI", "SCI-ELC"),
    ("EQ-SCI-008", "เครื่องวัดแสง", "เครื่องมือวิทยาศาสตร์", "UNI-T", "UT383", "1390", "DEMO-SCI", "SCI-LUX"),
    ("EQ-AV-001", "โปรเจกเตอร์", "โสตทัศนูปกรณ์", "Epson", "EB-E01", "17900", "DEMO-AV", "AV-PRO"),
    ("EQ-AV-002", "กล้องถ่ายภาพ", "โสตทัศนูปกรณ์", "Canon", "EOS R50", "28900", "DEMO-AV", "AV-CAM"),
    ("EQ-AV-003", "ขาตั้งกล้อง", "โสตทัศนูปกรณ์", "Manfrotto", "Compact Action", "3290", "DEMO-AV", "AV-TRI"),
    ("EQ-AV-004", "ลำโพงพกพา", "อุปกรณ์กิจกรรม", "JBL", "Charge 5", "5990", "DEMO-AV", "AV-SPK"),
    ("EQ-TOOL-001", "สว่านไฟฟ้า", "เครื่องมือช่าง", "Bosch", "GSB 550", "2990", "DEMO-GEN", "TOOL-DRL"),
    ("EQ-TOOL-002", "ชุดเครื่องมือช่าง", "เครื่องมือช่าง", "Stanley", "STMT81243", "4590", "DEMO-GEN", "TOOL-SET"),
    ("EQ-SAFE-001", "ชุดปฐมพยาบาล", "อุปกรณ์ความปลอดภัย", "3M", "Workplace Kit", "1590", "DEMO-GEN", "SAFE-FST"),
)

LOANS = (
    ("LOAN-DEMO-001", "BR-DEMO-001", "ST-DEMO-001", ("IT-NBK-001", "IT-MON-001"), 4, 2, "ยืมสำหรับจัดอบรมภายใน", "IT-MON-001", "available", "DEMO-IT", "อุปกรณ์สภาพสมบูรณ์"),
    ("LOAN-DEMO-002", "BR-DEMO-002", "ST-DEMO-002", ("SCI-MIC-001",), 7, -4, "ยืมสำหรับเก็บข้อมูลโครงการวิจัย", "SCI-MIC-001", "available", "DEMO-SCI", "ทำความสะอาดและจัดเก็บแล้ว"),
    ("LOAN-DEMO-003", "BR-DEMO-003", "ST-DEMO-001", ("SCI-PHM-001", "SCI-BAL-001"), 5, -1, "ยืมสำหรับตรวจสอบคุณภาพตัวอย่าง", "SCI-PHM-001", "maintenance", "DEMO-MAINT", "ค่าที่อ่านได้ไม่คงที่ ส่งตรวจเช็ก"),
    ("LOAN-DEMO-004", "BR-DEMO-004", "ST-DEMO-003", ("TOOL-DRL-001", "TOOL-SET-001"), 2, 1, "ยืมสำหรับงานติดตั้งพื้นที่กิจกรรม", "TOOL-DRL-001", "reported_lost", None, "ไม่พบอุปกรณ์หลังเสร็จงาน"),
    ("LOAN-DEMO-005", "BR-DEMO-005", "ST-DEMO-002", ("AV-CAM-001", "AV-SPK-001"), 1, 3, "ยืมสำหรับบันทึกภาพและจัดกิจกรรม", "AV-CAM-001", "available", "DEMO-AV", "คืนกล้องแล้ว เหลือลำโพงที่ยังใช้งานอยู่"),
)


def _row_id(database, table: str, code_column: str, code: str) -> int:
    row = database.execute(
        f"SELECT id FROM {table} WHERE {code_column} = ?", (code,)
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Seed record not found: {table}.{code_column}={code}")
    return row["id"]


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
                return False

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
                        "อุปกรณ์ตัวอย่างสำหรับระบบยืม–คืนอเนกประสงค์",
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
            return True
        except Exception:
            database.rollback()
            raise
