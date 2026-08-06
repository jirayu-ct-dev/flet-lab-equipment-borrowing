# แผนโครงการระบบยืม–คืนอุปกรณ์ห้องปฏิบัติการ

## 1. เป้าหมาย

สร้าง Flet Web app สำหรับเจ้าหน้าที่ห้องปฏิบัติการ เพื่อแทนการจดบันทึกด้วยกระดาษ
และทำให้สามารถตรวจสอบได้ว่าอุปกรณ์อยู่ที่ใคร เหลือพร้อมใช้เท่าใด กำหนดคืนเมื่อใด
และเคยถูกคืนในสภาพใด

MVP ให้ความสำคัญกับความถูกต้องของ inventory และประวัติการคืนก่อน Dashboard
หรือความสามารถด้าน presentation อื่น ๆ

## 2. ผู้ใช้งาน

### เจ้าหน้าที่ห้องปฏิบัติการ

- เพิ่ม แก้ไข ค้นหา และปิดการใช้งานอุปกรณ์
- เพิ่ม แก้ไข และค้นหาผู้ยืม
- บันทึกการยืมและการคืน
- ตรวจสอบรายการที่ยังไม่คืนหรือเกินกำหนด
- ตรวจสอบประวัติย้อนหลัง

### ผู้ยืม

นักศึกษา อาจารย์ หรือบุคลากรเป็นเจ้าของข้อมูลการยืม แต่ใน MVP เจ้าหน้าที่เป็นผู้ใช้ระบบแทนทั้งหมด
ผู้ยืมยังไม่มีบัญชีและไม่เข้าถึงระบบโดยตรง

## 3. ขอบเขต MVP

### 3.1 อุปกรณ์

ข้อมูลที่จัดเก็บ:

- รหัสและชื่ออุปกรณ์
- หมวดหมู่
- จำนวนทั้งหมดและจำนวนพร้อมใช้
- ตำแหน่งจัดเก็บ
- สถานะการใช้งาน เช่น `active`, `inactive`, `maintenance`
- รายละเอียดเพิ่มเติม

ระบบต้องเพิ่ม แก้ไข ค้นหา และปิดการใช้งานอุปกรณ์ได้ อุปกรณ์ที่มีประวัติการยืม
ต้องใช้ soft delete (`inactive`) แทนการลบถาวร

### 3.2 ผู้ยืม

ข้อมูลที่จัดเก็บ:

- รหัสนักศึกษาหรือรหัสบุคลากร
- ชื่อ–นามสกุล
- สาขาวิชาหรือหน่วยงาน
- เบอร์โทรศัพท์และอีเมล
- หมายเหตุ

ระบบต้องค้นหาผู้ยืมจากรหัสหรือชื่อได้

### 3.3 การยืม

รายการยืมหนึ่งรายการมีผู้ยืมหนึ่งคนและมีอุปกรณ์ได้หลายชนิด แต่ละชนิดระบุจำนวนได้
ระบบบันทึกเลขที่รายการ วันที่ยืม วันกำหนดคืน วัตถุประสงค์ ผู้บันทึก และหมายเหตุ

การสร้างรายการและลดจำนวนพร้อมใช้ต้องเกิดใน SQLite transaction เดียวกัน
หากขั้นตอนใดล้มเหลวต้อง rollback ทั้งหมด

### 3.4 การคืน

รายการยืมสามารถถูกคืนทั้งหมดหรือบางส่วนได้หลายครั้ง แต่ละครั้งต้องเก็บ:

- วันและเวลาที่คืน
- ผู้รับคืน
- อุปกรณ์และจำนวนที่คืน
- จำนวนที่กลับมาอยู่ในสภาพพร้อมใช้
- จำนวนที่ชำรุด อยู่ระหว่างซ่อม หรือสูญหาย
- ค่าปรับและหมายเหตุ

การสร้างเหตุการณ์คืนและการปรับจำนวนพร้อมใช้ต้องเกิดใน transaction เดียวกัน
เฉพาะจำนวนที่คืนในสภาพพร้อมใช้เท่านั้นที่เพิ่มกลับเข้า `available_quantity`

### 3.5 การค้นหาและประวัติ

ค้นหาและกรองได้จากรหัส/ชื่ออุปกรณ์ รหัส/ชื่อผู้ยืม วันยืม วันกำหนดคืน
และ lifecycle status ของรายการ ประวัติต้องแสดงเหตุการณ์คืนแต่ละครั้งแยกจากกัน

### 3.6 รายการเกินกำหนด

รายการถือว่าเกินกำหนดเมื่อวันปัจจุบันมากกว่า `due_date` และยังคืนไม่ครบ
ค่า `overdue` และ `due_soon` เป็นสถานะที่คำนวณตอน query ไม่จัดเก็บเป็น lifecycle status

## 4. นอกขอบเขต MVP

- Login, role และการยืนยันตัวตนผ่านบัญชีมหาวิทยาลัย
- หน้าสำหรับผู้ยืมดำเนินการด้วยตนเอง
- QR Code หรือ Barcode
- การอนุมัติหลายขั้นตอน
- การแจ้งเตือนผ่าน LINE หรืออีเมล
- รูปภาพอุปกรณ์
- รายงาน PDF/Excel
- ฐานข้อมูลออนไลน์และการใช้งานหลายสาขา
- Dashboard เชิงสถิติและอันดับอุปกรณ์ยอดนิยม

## 5. Data model

วันและเวลาจัดเก็บเป็น ISO 8601 text โดยแอปใช้ timezone เดียวกันตลอดทั้งระบบ
foreign key ทุกตัวต้องเปิดใช้งานผ่าน `PRAGMA foreign_keys = ON`

### `equipment`

| Field | Type | Constraint / ความหมาย |
|---|---|---|
| id | INTEGER | Primary key |
| equipment_code | TEXT | Unique, not null |
| name | TEXT | Not null |
| category | TEXT | หมวดหมู่ |
| total_quantity | INTEGER | `CHECK (total_quantity >= 0)` |
| available_quantity | INTEGER | `CHECK (available_quantity BETWEEN 0 AND total_quantity)` |
| location | TEXT | ตำแหน่งจัดเก็บ |
| status | TEXT | `active`, `inactive`, `maintenance` |
| description | TEXT | รายละเอียดเพิ่มเติม |
| created_at | TEXT | ISO 8601 timestamp |
| updated_at | TEXT | ISO 8601 timestamp |

### `borrowers`

| Field | Type | Constraint / ความหมาย |
|---|---|---|
| id | INTEGER | Primary key |
| borrower_code | TEXT | Unique, not null |
| full_name | TEXT | Not null |
| department | TEXT | สาขาหรือหน่วยงาน |
| phone | TEXT | เบอร์โทรศัพท์ |
| email | TEXT | อีเมล |
| note | TEXT | หมายเหตุ |
| created_at | TEXT | ISO 8601 timestamp |
| updated_at | TEXT | ISO 8601 timestamp |

### `borrow_transactions`

| Field | Type | Constraint / ความหมาย |
|---|---|---|
| id | INTEGER | Primary key |
| transaction_code | TEXT | Unique, not null |
| borrower_id | INTEGER | FK → `borrowers.id`, not null |
| borrow_date | TEXT | ISO 8601 date, not null |
| due_date | TEXT | ISO 8601 date, not null; ต้องไม่น้อยกว่า `borrow_date` |
| purpose | TEXT | วัตถุประสงค์ |
| recorded_by | TEXT | ผู้บันทึกรายการ, not null |
| status | TEXT | `active`, `completed`, `cancelled` |
| note | TEXT | หมายเหตุ |
| created_at | TEXT | ISO 8601 timestamp |
| updated_at | TEXT | ISO 8601 timestamp |

`partial`, `due_soon` และ `overdue` คำนวณจากรายการย่อย วันกำหนดคืน และเหตุการณ์คืน
ไม่จัดเก็บในคอลัมน์ `status`

### `borrow_items`

| Field | Type | Constraint / ความหมาย |
|---|---|---|
| id | INTEGER | Primary key |
| transaction_id | INTEGER | FK → `borrow_transactions.id`, not null |
| equipment_id | INTEGER | FK → `equipment.id`, not null |
| quantity | INTEGER | `CHECK (quantity > 0)` |

กำหนด `UNIQUE (transaction_id, equipment_id)` เพื่อไม่ให้อุปกรณ์ชนิดเดียวกันซ้ำในรายการเดียว

### `returns`

| Field | Type | Constraint / ความหมาย |
|---|---|---|
| id | INTEGER | Primary key |
| transaction_id | INTEGER | FK → `borrow_transactions.id`, not null |
| returned_at | TEXT | ISO 8601 timestamp, not null |
| received_by | TEXT | ผู้รับคืน, not null |
| fine_amount | NUMERIC | Default 0, ต้องไม่ติดลบ |
| note | TEXT | หมายเหตุ |
| created_at | TEXT | ISO 8601 timestamp |

### `return_items`

| Field | Type | Constraint / ความหมาย |
|---|---|---|
| id | INTEGER | Primary key |
| return_id | INTEGER | FK → `returns.id`, not null |
| borrow_item_id | INTEGER | FK → `borrow_items.id`, not null |
| usable_quantity | INTEGER | จำนวนที่กลับมาพร้อมใช้, ต้องไม่ติดลบ |
| damaged_quantity | INTEGER | จำนวนชำรุด, ต้องไม่ติดลบ |
| maintenance_quantity | INTEGER | จำนวนส่งซ่อม, ต้องไม่ติดลบ |
| lost_quantity | INTEGER | จำนวนสูญหาย, ต้องไม่ติดลบ |
| condition_note | TEXT | รายละเอียดสภาพ |

จำนวนคืนในหนึ่งแถวคือผลรวมของ quantity ทั้งสี่ประเภท และผลรวมการคืนทั้งหมดของ
`borrow_item_id` ต้องไม่เกิน `borrow_items.quantity` การตรวจข้ามหลายแถวนี้ทำใน service
ภายใน transaction เพราะ SQLite `CHECK` ไม่สามารถ aggregate แถวอื่นได้

## 6. Business rules และ invariants

1. จำนวนที่ยืมต้องมากกว่า 0 และไม่เกิน `available_quantity`
2. ยืมได้เฉพาะอุปกรณ์สถานะ `active`
3. วันกำหนดคืนต้องไม่น้อยกว่าวันยืม
4. จำนวนคืนสะสมต้องไม่เกินจำนวนที่ยืม
5. เฉพาะ `usable_quantity` เพิ่มกลับเข้า `available_quantity`
6. `available_quantity` ต้องอยู่ระหว่าง 0 และ `total_quantity` เสมอ
7. รายการเปลี่ยนเป็น `completed` เมื่อทุกรายการย่อยคืนครบ
8. รายการ `active` ที่คืนแล้วบางส่วนแสดง derived status เป็น `partial`
9. รายการ `active` ที่เกินกำหนดและยังคืนไม่ครบแสดง derived flag เป็น `overdue`
10. อุปกรณ์ที่มีประวัติใช้งานต้องปิดการใช้งานแทนการลบ
11. การยืมและการคืนแต่ละครั้งต้อง atomic: สำเร็จทั้งหมดหรือ rollback ทั้งหมด

## 7. User flow

### ยืมอุปกรณ์

1. เจ้าหน้าที่ค้นหาและเลือกผู้ยืม
2. เลือกอุปกรณ์สถานะ active และระบุจำนวน
3. ระบุวันยืม วันกำหนดคืน วัตถุประสงค์ และผู้บันทึก
4. ระบบตรวจข้อมูลและจำนวนพร้อมใช้ของทุกรายการอีกครั้งใน transaction
5. ระบบสร้าง transaction/items และลดจำนวนพร้อมใช้
6. ระบบ commit แล้วแสดงเลขที่รายการและยอดคงเหลือใหม่
7. ถ้าขั้นตอนใดล้มเหลว ระบบ rollback และแสดงข้อผิดพลาดโดยไม่เปลี่ยนยอด

### คืนอุปกรณ์

1. เจ้าหน้าที่ค้นหารายการ `active`
2. ระบบแสดงจำนวนที่ยืม จำนวนที่คืนแล้ว และจำนวนที่ยังค้างแยกรายการ
3. เจ้าหน้าที่ระบุจำนวนตามสภาพ พร้อมผู้รับคืนและหมายเหตุ
4. ระบบตรวจว่าจำนวนคืนใหม่ไม่เกินจำนวนค้าง
5. ระบบสร้าง return event และเพิ่มเฉพาะจำนวนพร้อมใช้ใน transaction เดียวกัน
6. ระบบเปลี่ยน lifecycle status เป็น `completed` เมื่อคืนครบทุก item
7. ระบบ commit และแสดงยอดใหม่ หรือ rollback ทั้งหมดหากเกิดข้อผิดพลาด

## 8. หน้าจอ MVP

เริ่มจากหน้าจอเท่าที่จำเป็นต่อ vertical slice:

1. Equipment — รายการ เพิ่ม แก้ไข ค้นหา และปิดการใช้งาน
2. Borrowers — รายการ เพิ่ม แก้ไข และค้นหา
3. Borrow — สร้างรายการยืม
4. Active Loans — ค้นหารายการค้าง/เกินกำหนดและบันทึกการคืน
5. History — ดูรายการยืมและ return events

Dashboard เป็นงานหลัง MVP เมื่อข้อมูลและ query หลักได้รับการทดสอบแล้ว

## 9. ลำดับการพัฒนา

### Phase 1 — Database และ domain services

- สร้าง schema, constraints และ database initialization
- สร้าง equipment/borrower services
- สร้าง borrow/return services พร้อม transaction boundary
- เขียน integration tests ด้วย temporary SQLite database

**ผ่านเมื่อ:** tests ครอบคลุม CRUD หลัก, ยืมสำเร็จ, ยืมเกิน, คืนเต็ม, คืนบางส่วนหลายครั้ง,
คืนของหลายสภาพ, คืนเกิน และ rollback โดยทุกกรณีรักษา inventory invariant

### Phase 2 — Vertical slice บน Flet Web

- สร้าง navigation และห้าหน้าจอ MVP
- เชื่อม UI กับ services โดยไม่เขียน SQL ใน view
- แสดง validation error และผลการบันทึกให้ผู้ใช้ทราบ

**ผ่านเมื่อ:** เจ้าหน้าที่ทำ flow ยืมและคืนบางส่วนตั้งแต่ต้นจนจบผ่าน UI ได้
และข้อมูลยังคงอยู่หลัง restart

### Phase 3 — Search, overdue และ usability

- เพิ่มการค้นหาและ filter
- เพิ่ม derived flags สำหรับ partial, due soon และ overdue
- ปรับ responsive layout และ empty/error states

**ผ่านเมื่อ:** acceptance scenarios ด้านการค้นหาและ overdue ผ่านทั้ง service test และ UI smoke test

### Phase 4 — Dashboard หลัง MVP

- เพิ่มยอดอุปกรณ์และรายการยืมที่สำคัญ
- เพิ่มรายการยืมล่าสุด
- ประเมิน metric อุปกรณ์ถูกยืมบ่อยจากข้อมูลใช้งานจริง

## 10. Acceptance criteria

MVP พร้อมใช้งานเมื่อ:

- เพิ่ม แก้ไข ค้นหา และปิดใช้งานอุปกรณ์ได้
- เพิ่ม แก้ไข และค้นหาผู้ยืมได้
- รายการยืมมีอุปกรณ์หลายชนิดได้ และไม่สามารถยืมเกินจำนวนพร้อมใช้
- คืนทั้งหมดหรือบางส่วนหลายครั้งได้โดยประวัติแต่ละครั้งไม่ถูกเขียนทับ
- ของชำรุด/ซ่อม/สูญหายไม่เพิ่มกลับเป็นจำนวนพร้อมใช้
- ไม่สามารถคืนสะสมเกินจำนวนที่ยืม
- ความล้มเหลวระหว่างบันทึกไม่สร้างรายการครึ่งเดียวหรือยอดคงเหลือผิด
- แสดงรายการค้างและรายการเกินกำหนดจากวันปัจจุบันได้โดยไม่ต้องแก้ status ในฐานข้อมูล
- ค้นหาประวัติจากผู้ยืม อุปกรณ์ และช่วงวันที่ได้
- ปิดและเปิดแอปใหม่แล้วข้อมูลยังอยู่ครบ

## 11. ความเสี่ยงและข้อจำกัด

- SQLite เหมาะกับ MVP แบบเจ้าหน้าที่จำนวนน้อย ไม่ใช่ระบบหลายสาขาหรือ write concurrency สูง
- `available_quantity` เป็นค่าที่เก็บซ้ำเพื่ออ่านเร็ว จึงต้องแก้พร้อม loan/return ใน transaction เดียวเสมอ
- การแบ่งจำนวนตามสภาพรองรับอุปกรณ์แบบนับจำนวน หากต้องติดตาม serial number รายชิ้นต้องออกแบบ asset table เพิ่มในอนาคต
- ก่อน deploy ต้องกำหนด timezone, backup policy และที่เก็บไฟล์ฐานข้อมูลให้ชัดเจน

## 12. Future features

- Authentication และ role-based access
- University SSO
- QR/Barcode
- LINE หรือ email notifications
- รูปภาพอุปกรณ์
- รายงาน PDF/Excel
- Audit log สำหรับการแก้ไขข้อมูล
- Backup/restore
- PostgreSQL และ deployment บน server/cloud
