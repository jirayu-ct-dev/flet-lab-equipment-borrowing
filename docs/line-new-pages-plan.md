# แผนเพิ่มหน้าใหม่ตาม LINE Richmenu Routing

อ้างอิง: `docs/line-richmenu-routing.md`

## 1. หน้าใหม่ที่ต้องสร้าง

| Route | ชื่อหน้า | ประเภท | ผู้ใช้ |
|---|---|---|---|
| `/report_lost` | แจ้งอุปกรณ์หาย | ฟอร์ม + ข้อมูล (ใหญ่สุด) | user (ผู้ยืม) |
| `/guide` | คู่มือการใช้งาน | static content | ทุกคน |
| `/contact` | ติดต่อเจ้าหน้าที่ | แสดงรายชื่อ staff | ทุกคน |

**หมายเหตุหน้าใน new-user richmenu:**
- `/register` → **ตัดออก** — การสมัครเกิดอัตโนมัติตอน LINE Login อยู่แล้ว (ไม่มีหน้า register)
- `/about`, `/faq` → **รวมไว้ใน `/guide`** เป็น section แทน (ไม่สร้างหน้าแยก)
- `/login` → ใช้ root path เดิม (หน้า login มีอยู่แล้ว)

## 2. หน้า `/report_lost` — แจ้งอุปกรณ์หาย

### 2.1 Flow ที่เสนอ

```
1. ผู้ยืมกด "แจ้งหาย" (จาก richmenu หรือ nav)
2. เห็นรายการอุปกรณ์ที่ตัวเองยังยืมอยู่ (จาก list_loans_for_borrower)
3. เลือกชิ้นที่หาย → กรอก: วันที่หาย, สถานที่, คำอธิบาย
4. Submit → สร้าง lost_reports (status = pending)
5. Admin เห็นรายการ "รอตรวจ" ใน Dashboard (ส่วนใหม่)
   → อนุมัติ: unit → reported_lost + สร้าง lost_case (resolution = NULL)
   → ปฏิเสธ: จบ (บันทึกเหตุผล)
6. lost_case ที่สร้าง → เข้า workflow เดิมบน Dashboard ต่อ
   (ประเมินราคา → ชดเชย/จัดหาทดแทน/ปิดเคส)
```

### 2.2 Data Model (migration ใหม่ append ใน MIGRATIONS)

```sql
CREATE TABLE lost_reports (
    id INTEGER PRIMARY KEY,
    borrower_id INTEGER NOT NULL REFERENCES borrowers(id),
    equipment_unit_id INTEGER NOT NULL REFERENCES equipment_units(id),
    reported_at TEXT NOT NULL,
    lost_date TEXT,
    location TEXT,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by_staff_id INTEGER REFERENCES staff(id),
    reviewed_at TEXT,
    review_note TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
```

### 2.3 Layer Changes

| Layer | งาน |
|---|---|
| `app/contracts.py` | `LostReport` dataclass, `CreateLostReport`, `ReviewLostReport` commands, `LostReportService` Protocol |
| `app/database.py` | migration ใหม่ (ตาราง `lost_reports`) |
| `app/repositories/lost_report_repository.py` (ใหม่) | raw SQL: create / list_pending / list_by_borrower / review |
| `app/services/fake_services.py` | `FakeLostReportService` (in-memory) |
| `app/services/sqlite_adapter.py` | `SQLiteLostReportAdapter` — **fake/SQLite sync ตาม AGENTS.md** |
| `app/services/container.py` | เพิ่ม lost-report service ใน AppServices |
| `app/errors.py` | ใช้ `DomainError` เดิม (ไม่มี error ใหม่ถ้าไม่จำเป็น) |

API ที่เสนอ (ทั้ง fake + SQLite เหมือนกัน):

```python
def create_report(command: CreateLostReport) -> LostReport
def list_pending_reports() -> list[LostReport]
def list_reports_for_borrower(borrower_id: int) -> list[LostReport]
def review_report(report_id: int, command: ReviewLostReport) -> LostReport
    # approve: unit.status → reported_lost + สร้าง lost_case (resolution=None)
    # reject: บันทึก review_note เท่านั้น
```

### 2.4 View — `app/views/report_lost.py`

- Pattern เดียวกับ `my_loans.py` (table/cards สลับตาม breakpoint, `build_table_surface(initial_width/on_resized)`, `handle_mobile_resize`, ห้าม expand=False)
- Desktop: ตาราง [รหัส, ชื่ออุปกรณ์, ครบกำหนด, สถานะ, ปุ่มแจ้งหาย] + ฟอร์มใน dialog (`build_form_dialog`)
- Mobile: `build_card_list` + ปุ่มใน `build_data_card.actions`
- แสดงรายการ report ที่เคยแจ้งไว้ด้านล่าง (สถานะ pending/approved/rejected)
- Guard: `has_permission(current_user, Permission.VIEW_MY_LOANS)` + `borrower_id` ต้องไม่ None (เหมือน my_loans)
- Feedback ไทยครบ: "แจ้งอุปกรณ์หายเรียบร้อย", "กรุณาเลือกอุปกรณ์ที่ต้องการแจ้ง", ฯลฯ

### 2.5 ฝั่ง Admin (Dashboard)

- เพิ่มส่วน "รายงานอุปกรณ์หายรอตรวจ" — แสดง pending reports + ปุ่ม อนุมัติ/ปฏิเสธ
- อนุมัติ → `review_report(...)` → unit กลายเป็น reported_lost + lost_case เข้า workflow เดิม
- ต้องไม่กระทบ metric/ตารางเดิมของ Dashboard (เพิ่ม section อย่างเดียว)

### 2.6 Permissions & Nav

- เพิ่ม nav item "แจ้งหาย" (icon `REPORT_PROBLEM_OUTLINED`, route `report_lost`) — แสดงเฉพาะ user role (`Permission.VIEW_MY_LOANS`)
- user nav: อุปกรณ์, ของฉัน, ประวัติ, **แจ้งหาย** (4 items)
- admin nav: 6 items เดิม (admin ไม่เห็น แจ้งหาย ใน nav — แต่เข้าถึง route ได้จาก richmenu)

## 3. หน้า `/guide` — คู่มือการใช้งาน

- `app/views/guide.py` — `build_guide_view(mobile)` — static ไม่แตะ service
- Content (build_page_header + build_card sections):
  1. ระบบนี้คืออะไร (ย่อจาก docs/project-story.md)
  2. วิธีดูอุปกรณ์และสถานะ
  3. วิธียืม/คืน (สำหรับเจ้าหน้าที่)
  4. หน้า "ของฉัน" และกำหนดคืน (สำหรับผู้ยืม)
  5. แจ้งอุปกรณ์หาย
  6. คำถามที่พบบ่อย (FAQ)
- Desktop: Column ของ cards; Mobile: card list — scroll ได้

## 4. หน้า `/contact` — ติดต่อเจ้าหน้าที่

- `app/views/contact.py` — `ContactView(service, *, mobile)`
- ข้อมูลจาก `service.list_staff()` (มีอยู่แล้ว) → การ์ด: ชื่อ, ตำแหน่ง, email, โทร
- ไม่มี staff → `build_state_view("ไม่พบข้อมูลเจ้าหน้าที่", ...)`
- Desktop: ตาราง/การ์ด grid; Mobile: card list

## 5. main.py & Routes

```python
# navigate_to(item) เพิ่ม:
elif item["route"] == "report_lost":
    content_area.content = build_screen(
        ReportLostView(service, current_user=current_user, mobile=is_mobile)
    )
elif item["route"] == "guide":
    content_area.content = build_screen(build_guide_view(mobile=is_mobile))
elif item["route"] == "contact":
    content_area.content = build_screen(
        ContactView(service, mobile=is_mobile)
    )
```

- `theme.py` NAVIGATION_ITEMS + `main.py` get_navigation_items(): เพิ่ม "แจ้งหาย" (เฉพาะ role user เห็น ผ่าน `visible_navigation_items`)
- guide/contact: **ไม่เพิ่มใน nav** — เข้าผ่าน richmenu อย่างเดียว (กัน nav ยาว)

## 6. Tests

| ไฟล์ | ครอบคลุม |
|---|---|
| `tests/test_lost_report_service.py` (ใหม่) | fake service: create, list pending, review approve → unit reported_lost + lost_case เกิด, reject |
| `tests/integration/test_lost_report_sqlite.py` (ใหม่) | migration + adapter CRUD + approve flow บน tmp DB |
| `tests/test_report_lost_view.py` (ใหม่) | ฟอร์ม/ตาราง/cards, guard (user ไม่มีสิทธิ์/ไม่มี borrower_id), feedback |
| `tests/test_guide_view.py`, `tests/test_contact_view.py` (ใหม่) | structure + empty state |
| `tests/test_main_auth.py` | user nav = 4 items, navigate_to report_lost/guide/contact |
| `tests/test_layout_guards.py` | เพิ่ม 3 views ใหม่เข้า build list (ไม่มี expand=False) |

## 7. ลำดับการทำ

1. **Data layer**: migration + contracts + repository + services (fake/SQLite) + tests
2. **report_lost view** + nav + main.py route + admin dashboard section + tests
3. **guide + contact** (static/ง่าย) + routes + tests
4. อัปเดต richmenu JSON (แทน `<host>` ด้วย domain จริง) + test เปิดจาก LINE จริง

## 8. ขอบเขตที่ตัดออก (ไม่ทำในรอบนี้)

- การแจ้งหายอัตโนมัติผ่าน Messaging API แจ้งเตือน admin
- การแนบรูปภาพในรายงาน
- หน้า `/register` แยก (สมัครผ่าน LINE login อัตโนมัติ)
- `/about`, `/faq` แยกหน้า (รวมใน guide)
