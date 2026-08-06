# แผนโครงการระบบยืม–คืนอุปกรณ์ห้องปฏิบัติการ

## 1. เป้าหมาย

สร้าง Flet Web app สำหรับเจ้าหน้าที่ห้องปฏิบัติการ เพื่อจัดเก็บอุปกรณ์รายชิ้น ผู้ยืม
การยืม–คืน ตำแหน่ง สภาพ และประวัติการเปลี่ยนแปลงอย่างตรวจสอบย้อนหลังได้

MVP ให้ความสำคัญกับความถูกต้องของ inventory และ transaction ก่อน Dashboard
การแจ้งเตือน หรือรายงานขั้นสูง

## 2. ข้อตกลงผลิตภัณฑ์ที่ยืนยันแล้ว

1. อุปกรณ์ทุกชิ้นมีรหัสภายในและถูกติดตามแยกกัน ไม่มีโหมดจำนวนรวมใน MVP
2. มีตารางเจ้าหน้าที่ แต่ยังไม่มี login; ผู้ใช้ต้องเลือกเจ้าหน้าที่ผู้ดำเนินการ
3. ระบบใช้ timezone `Asia/Bangkok`
4. `due_soon` หมายถึงเหลือ 1–3 วันปฏิทินและยังคืนไม่ครบ
5. อุปกรณ์สูญหายต้องผ่านกระบวนการชดใช้หรือยกเว้น ไม่ถือว่าคืนแล้วทันที
6. รายการที่ยืนยันแล้วแก้ไขได้เฉพาะข้อมูลที่ไม่กระทบ inventory; การแก้ไขต้องมีเหตุผลและ audit log
7. ห้ามแก้จำนวนคงเหลือโดยตรง การเพิ่มหรือลดอุปกรณ์ทำผ่าน inventory adjustment
8. รายการยืม คืน และ audit log ที่ยืนยันแล้วห้ามลบถาวร

## 3. ผู้ใช้งาน

### เจ้าหน้าที่ห้องปฏิบัติการ

- จัดการประเภทอุปกรณ์ อุปกรณ์รายชิ้น ตำแหน่ง ผู้ยืม และข้อมูลเจ้าหน้าที่
- บันทึกการยืม คืน ชำรุด ซ่อม สูญหาย และการชดใช้
- ค้นหารายการค้าง ใกล้ครบกำหนด เกินกำหนด และประวัติย้อนหลัง

### ผู้ยืม

นักศึกษา อาจารย์ หรือบุคลากรเป็นเจ้าของรายการยืม แต่ไม่มีบัญชีและไม่ใช้งานระบบโดยตรงใน MVP

## 4. ขอบเขต MVP

### 4.1 ประเภทอุปกรณ์และอุปกรณ์รายชิ้น

`equipment` เก็บข้อมูลประเภทหรือรุ่น เช่น “Notebook Dell Latitude” ส่วน `equipment_units`
เก็บอุปกรณ์จริงแต่ละชิ้น เช่น `NB-0001`

ทุก unit มีสถานะหนึ่งค่า:

- `available`
- `borrowed`
- `maintenance`
- `reported_lost`
- `retired`

ตำแหน่งจัดเก็บประกอบด้วยอาคาร ห้อง ตู้ และชั้น โดย unit ที่ถูกยืมให้ถือว่าอยู่กับผู้ยืม
ตำแหน่งไม่ได้มาจาก GPS แต่เป็นข้อมูลที่เจ้าหน้าที่บันทึก

### 4.2 เจ้าหน้าที่

ระบบเก็บรหัส ชื่อ ข้อมูลติดต่อ และสถานะ active/inactive ของเจ้าหน้าที่ เจ้าหน้าที่ inactive
ยังคงปรากฏในประวัติแต่ไม่สามารถถูกเลือกสำหรับรายการใหม่

### 4.3 ผู้ยืม

ระบบเก็บรหัส ชื่อ หน่วยงาน เบอร์โทรศัพท์ อีเมล และหมายเหตุ ค้นหาได้จากรหัสหรือชื่อ

### 4.4 การยืม

รายการยืมหนึ่งรายการมีผู้ยืมหนึ่งคนและมีอุปกรณ์หลาย unit ได้ การยืนยันรายการต้องตรวจว่า
ทุก unit เป็น `available` แล้วเปลี่ยนเป็น `borrowed` ใน SQLite transaction เดียวกัน

### 4.5 การคืน

รายการหนึ่งคืนทั้งหมดหรือบางส่วนได้หลายครั้ง แต่ละ return event เก็บวันเวลา ผู้รับคืน
unit ที่คืน สภาพ และหมายเหตุ

- คืนปกติ → `available`
- ต้องซ่อม/ชำรุด → `maintenance`
- แจ้งสูญหาย → `reported_lost` และเปิด lost case

### 4.6 สูญหายและการชดใช้

Lost case ปิดได้ด้วย resolution ต่อไปนี้:

- `recovered` — พบและรับอุปกรณ์เดิมคืน
- `replaced` — ได้รับอุปกรณ์ทดแทน
- `compensated` — ชำระเงินตามมูลค่าที่อนุมัติ
- `waived` — ผู้มีอำนาจยกเว้น

ระบบเก็บราคาซื้อเดิม มูลค่าประเมิน มูลค่าชดใช้ที่อนุมัติ วิธีชดใช้ ผู้อนุมัติ
วันเวลาที่เสร็จสิ้น และหมายเหตุ ระบบอาจแสดงราคาเพื่อช่วยตัดสินใจ แต่ห้ามอนุมัติยอดอัตโนมัติ

### 4.7 การแก้ไขและ audit

ก่อนยืนยัน รายการยืมแก้ไขได้ทั้งหมด หลังยืนยันแก้ได้เฉพาะ due date, purpose, note
และข้อมูลติดต่อผู้ยืม การเปลี่ยน unit หรือผู้ยืมต้องใช้ action เฉพาะและระบุเหตุผล

Audit log เก็บ entity, entity id, action, ค่าเดิม, ค่าใหม่, เหตุผล, เจ้าหน้าที่ และ timestamp

### 4.8 ค้นหาและสถานะตามเวลา

- `due_today`: ครบกำหนดวันนี้และยังมี unit ค้าง
- `due_soon`: เหลือ 1–3 วันและยังมี unit ค้าง
- `overdue`: วันนี้มากกว่า due date และยังมี unit ค้าง
- `partial`: คืนแล้วบางส่วนแต่ยังไม่ครบ

สถานะเหล่านี้คำนวณตอน query ไม่จัดเก็บเป็น lifecycle status

## 5. นอกขอบเขต MVP

- Login, role enforcement และ University SSO
- GPS หรือการติดตามตำแหน่งอัตโนมัติ
- อุปกรณ์แบบ bulk quantity
- QR/Barcode
- การอนุมัติหลายขั้นตอน
- LINE/email notifications
- รูปภาพ รายงาน PDF/Excel และ Dashboard เชิงสถิติ
- หลายสาขา PostgreSQL และ cloud deployment

## 6. Data model

Foreign key ต้องเปิดด้วย `PRAGMA foreign_keys = ON` รหัสธุรกิจทุกชนิดเป็น unique และห้ามนำกลับมาใช้ใหม่
วันที่ธุรกิจใช้ Bangkok local date ส่วน timestamp จัดเก็บเป็น UTC ISO 8601 แล้วแปลงเป็น
`Asia/Bangkok` ตอนแสดงผล

### `equipment`

| Field | Constraint / ความหมาย |
|---|---|
| id | Primary key |
| equipment_code | Unique, immutable |
| name | Not null |
| category | หมวดหมู่ |
| manufacturer | ผู้ผลิต |
| model | รุ่น |
| default_location_id | FK → `locations.id`, nullable |
| purchase_price | ต้องไม่ติดลบ, nullable |
| status | `active`, `inactive` |
| description | รายละเอียด |
| created_at, updated_at | UTC timestamp |

### `equipment_units`

| Field | Constraint / ความหมาย |
|---|---|
| id | Primary key |
| asset_code | Unique, immutable |
| equipment_id | FK → `equipment.id`, not null |
| serial_number | Unique เมื่อมีค่า |
| current_location_id | FK → `locations.id`, nullable ขณะถูกยืม |
| status | `available`, `borrowed`, `maintenance`, `reported_lost`, `retired` |
| acquired_at | วันที่รับเข้า |
| purchase_price | ราคาของ unit ถ้าต่างจากค่า default |
| note | หมายเหตุ |
| created_at, updated_at | UTC timestamp |

### `locations`

| Field | Constraint / ความหมาย |
|---|---|
| id | Primary key |
| location_code | Unique |
| building | อาคาร |
| room | ห้อง, not null |
| cabinet | ตู้, nullable |
| shelf | ชั้น, nullable |
| status | `active`, `inactive` |

### `staff`

| Field | Constraint / ความหมาย |
|---|---|
| id | Primary key |
| staff_code | Unique, immutable |
| full_name | Not null |
| email, phone | ข้อมูลติดต่อ |
| status | `active`, `inactive` |
| created_at, updated_at | UTC timestamp |

### `borrowers`

| Field | Constraint / ความหมาย |
|---|---|
| id | Primary key |
| borrower_code | Unique, immutable |
| full_name | Not null |
| department | หน่วยงาน |
| email, phone | ข้อมูลติดต่อ |
| note | หมายเหตุ |
| status | `active`, `inactive` |
| created_at, updated_at | UTC timestamp |

### `borrow_transactions`

| Field | Constraint / ความหมาย |
|---|---|
| id | Primary key |
| transaction_code | Unique, immutable |
| borrower_id | FK → `borrowers.id` |
| borrow_date | Bangkok local date |
| due_date | ต้องไม่น้อยกว่า borrow date |
| purpose | วัตถุประสงค์ |
| recorded_by_staff_id | FK → `staff.id` |
| status | `draft`, `active`, `completed`, `cancelled` |
| note | หมายเหตุ |
| created_at, updated_at | UTC timestamp |

### `borrow_items`

| Field | Constraint / ความหมาย |
|---|---|
| id | Primary key |
| transaction_id | FK → `borrow_transactions.id` |
| equipment_unit_id | FK → `equipment_units.id` |

กำหนด `UNIQUE(transaction_id, equipment_unit_id)` และห้าม unit อยู่ใน active loan มากกว่าหนึ่งรายการ

### `returns` และ `return_items`

`returns` เก็บ transaction, returned_at, received_by_staff_id และ note ส่วน `return_items`
เก็บ return id, borrow item id, outcome (`available`, `maintenance`, `reported_lost`) และ condition note
หนึ่ง borrow item ปิดด้วย return item ได้เพียงครั้งเดียว

### `lost_cases`

เก็บ equipment unit, borrow item, reported_at, assessed value, approved compensation,
resolution, approved_by_staff_id, resolved_at และ note หนึ่ง borrow item มี active lost case ได้หนึ่งรายการ

### `inventory_adjustments`

เก็บ unit, action (`acquire`, `retire`, `relocate`, `repair_complete`), เหตุผล, เจ้าหน้าที่
และ timestamp ห้ามแก้ status/location ของ unit โดยข้าม service นี้ ยกเว้น borrow/return service

### `audit_logs`

เก็บ entity type/id, action, before/after JSON, reason, staff id และ timestamp
ตารางนี้ append-only

## 7. Business rules

1. ยืมได้เฉพาะ unit สถานะ `available`
2. การยืนยัน loan และเปลี่ยนทุก unit เป็น `borrowed` ต้อง atomic
3. การคืนและเปลี่ยนสถานะทุก unit ต้อง atomic
4. Unit ที่ถูกยืมห้าม retire, relocate หรืออยู่ใน active loan อื่น
5. Unit สูญหายไม่ถือว่าคืนเสร็จจน lost case มี resolution
6. Unit ที่ recovered กลับตามผลตรวจสภาพ; replacement ต้องสร้าง asset code ใหม่
7. Unit code, transaction code และรหัสบุคคลห้ามนำกลับมาใช้ใหม่
8. ห้ามลบประวัติที่ยืนยันแล้ว ใช้ cancel/adjustment พร้อมเหตุผล
9. การแก้รายการ active ต้องสร้าง audit log
10. เวลาปัจจุบันสำหรับ overdue มาจาก backend clock ไม่ใช่ browser

## 8. Service contract ระหว่าง Frontend และ Backend

Flet views เรียก service methods และรับ dataclass/DTO เท่านั้น ห้าม import `sqlite3` หรือใช้ SQL

Backend ต้องเผยแพร่ contract สำหรับ:

- DTO ของ equipment, unit, location, staff, borrower, loan, return และ lost case
- create/update command objects
- search/filter parameters
- domain errors เช่น `UnitNotAvailable`, `ReturnAlreadyRecorded`, `ValidationError`
- transaction methods เช่น `confirm_loan()`, `record_return()`, `resolve_lost_case()`

Frontend สร้าง fake services ตาม contract เดียวกันเพื่อพัฒนา UI คู่ขนาน Contract ที่ merge แล้ว
เปลี่ยนได้ผ่าน PR ที่ทั้ง frontend และ backend review

## 9. User flows สำคัญ

### รับอุปกรณ์ใหม่

1. เลือกหรือสร้างประเภทอุปกรณ์
2. ระบุ asset code, serial number, ราคา และตำแหน่ง
3. เลือกเจ้าหน้าที่และบันทึก
4. Backend สร้าง unit และ acquire adjustment ใน transaction เดียวกัน

### ยืม

1. เลือกเจ้าหน้าที่และผู้ยืม
2. เลือก available units
3. ระบุวันยืม วันกำหนดคืน และวัตถุประสงค์
4. Backend ตรวจสถานะอีกครั้ง ยืนยันรายการ และเปลี่ยน units เป็น borrowed

### คืน

1. เปิด active loan และเลือก units ที่ต้องการคืน
2. ระบุ outcome และสภาพแต่ละ unit
3. Backend สร้าง return event และเปลี่ยนสถานะใน transaction เดียวกัน
4. Loan เป็น completed เมื่อทุก item คืนหรือมี lost resolution แล้ว

### สูญหาย

1. ระบุ unit เป็น reported lost และเปิด lost case
2. บันทึกมูลค่าประเมินและยอดที่เจ้าหน้าที่อนุมัติ
3. เลือก resolution พร้อมผู้อนุมัติและหลักฐาน/หมายเหตุ
4. Backend ปิด case, audit และอัปเดต unit ตาม resolution

## 10. Milestones

### M1 — Inventory foundation

จัดการ equipment, units, locations และ staff พร้อมข้อมูลคงอยู่หลัง restart

### M2 — Borrower และ borrow flow

สร้างผู้ยืม ยืนยัน loan หลาย unit และป้องกัน unit เดียวอยู่สอง active loans

### M3 — Return และ history

คืนบางส่วนหลายครั้ง รองรับ maintenance และแสดงประวัติครบ

### M4 — Lost, edit และ audit

จัดการของสูญหาย การชดใช้ การแก้ due date และ audit log

### M5 — Search และ usability

ค้นหา filter due soon/due today/overdue และปรับ responsive/error states

รายละเอียดการมอบหมายอยู่ใน [Frontend Scope](scopes/frontend.md) และ
[Backend Scope](scopes/backend.md)

## 11. Acceptance criteria ของ MVP

- อุปกรณ์ทุกชิ้นมี asset code ไม่ซ้ำและทราบสถานะ/ตำแหน่งล่าสุด
- เจ้าหน้าที่ inactive ไม่ถูกเลือกในรายการใหม่แต่ประวัติยังอยู่
- unit เดียวไม่อยู่ใน active loans สองรายการ
- คืนบางส่วนหลายครั้งได้โดยประวัติไม่ถูกเขียนทับ
- ของชำรุดไม่กลับเป็น available และของสูญหายมี lost case
- ค่าชดใช้ต้องมีผู้อนุมัติและไม่ถูกคำนวณอนุมัติอัตโนมัติ
- การแก้รายการ active และ inventory adjustment มีเหตุผลและ audit log
- due soon ใช้ 3 วันและคำนวณด้วยเวลา Asia/Bangkok
- ความล้มเหลวระหว่าง transaction ไม่สร้างข้อมูลครึ่งเดียว
- ค้นหาจากผู้ยืม อุปกรณ์ asset code และช่วงวันที่ได้
- local และ Docker ใช้ database เดิมหลัง restart

## 12. ความเสี่ยงและข้อจำกัด

- SQLite เหมาะกับ MVP เจ้าหน้าที่จำนวนน้อย ไม่เหมาะกับ write concurrency สูง
- การไม่มี login ทำให้ข้อมูลผู้ดำเนินการเป็นการเลือกชื่อ ไม่ใช่หลักฐานยืนยันตัวตน
- การติดตามรายชิ้นต้องใช้เวลาลงทะเบียน asset codes ก่อนใช้งานจริง
- ก่อน production ต้องกำหนด backup, retention และสิทธิ์เข้าถึงไฟล์ฐานข้อมูล
