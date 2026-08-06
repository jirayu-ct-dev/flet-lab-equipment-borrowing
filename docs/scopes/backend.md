# Backend Scope

## เป้าหมาย

สร้าง SQLite persistence และ domain services ที่รักษาความถูกต้องของอุปกรณ์รายชิ้น
โดย Frontend ใช้งานผ่าน Python service contract และไม่ต้องรู้รายละเอียด SQL

## Ownership

Backend เป็น owner ของ:

```text
app/database.py
app/models.py หรือ app/contracts.py
app/services/
app/repositories/
tests/integration/
```

การแก้ contract ต้องให้ Frontend review ส่วน `main.py`, `app/views/` และ `app/components/`
ไม่อยู่ใน ownership ของ Backend

## งานตามลำดับ

### BE-01 — Database foundation

- สร้าง package structure และ database connection factory
- อ่าน path จาก `APP_DB_PATH`
- เปิด foreign keys ทุก connection
- สร้าง schema versioning ที่เรียบง่าย
- ใช้ UTC timestamps และ Bangkok business dates

**Acceptance:** temporary SQLite database initialize ซ้ำได้, constraints ทำงาน และไฟล์จริงคงอยู่หลัง restart

### BE-02 — Contracts และ domain errors

- DTO/commands สำหรับ location, equipment, unit, staff และ borrower
- protocols/interfaces ที่ fake service และ SQLite service ใช้ร่วมกัน
- validation/domain errors ที่ UI แปลงเป็นข้อความได้

**Acceptance:** Frontend import contract ได้โดยไม่ import database implementation

### BE-03 — Master data services

- CRUD/search สำหรับ location, equipment, unit, staff และ borrower
- ใช้ inactive/retired แทน hard delete
- asset code และ business codes immutable
- acquire, relocate, retire และ repair-complete adjustments

**Acceptance:** integration tests ครอบคลุม duplicate codes, invalid transitions และ inactive records

### BE-04 — Borrow service

- สร้าง draft และยืนยัน loan หลาย unit
- ตรวจ borrower/staff active และ unit available
- เปลี่ยนทุก unit เป็น borrowed แบบ atomic
- ป้องกัน double loan

**Acceptance:** concurrent/stale selection ไม่ทำให้ unit อยู่ใน active loans สองรายการ และ failure rollback ทั้งหมด

### BE-05 — Return service

- คืนบางส่วนได้หลายครั้ง
- outcome เป็น available, maintenance หรือ reported_lost
- ป้องกันคืนซ้ำ
- ปิด loan เมื่อทุก item resolved

**Acceptance:** return event ไม่ถูกเขียนทับ, invalid return rollback และ status ทุก unit ถูกต้อง

### BE-06 — Lost resolution

- เปิด lost case จาก return outcome
- เก็บ assessed/approved amounts และ approver
- รองรับ recovered, replaced, compensated และ waived
- replacement สร้าง unit ใหม่ ไม่เปลี่ยน identity ของ unit เดิม

**Acceptance:** case ปิดไม่ได้หากข้อมูลอนุมัติไม่ครบ และทุก resolution มี audit trail

### BE-07 — Edit และ audit

- แก้ due date, purpose และ note พร้อมเหตุผล
- action เฉพาะสำหรับเปลี่ยนผู้ยืมหรือ unit
- audit logs เป็น append-only

**Acceptance:** before/after, reason, staff และ timestamp ถูกบันทึกทุกครั้ง

### BE-08 — Query services

- ค้นหา active, partial, due today, due soon และ overdue
- ใช้ backend clock และ Asia/Bangkok
- ค้นหาจาก borrower, equipment, asset code และช่วงวันที่

**Acceptance:** boundary tests สำหรับ 3 วัน, วันนี้ และวันถัดจาก due date ผ่าน

## Test requirements

- ใช้ temporary SQLite database ไม่ mock SQL ใน integration tests
- ทดสอบ success, validation, invalid transition และ rollback
- ทดสอบ restart/persistence
- services ต้องรับ clock dependency สำหรับทดสอบเวลาได้

## ไม่อยู่ในขอบเขต Backend MVP

- REST API/FastAPI แยกต่างหาก
- Authentication และ role enforcement
- PostgreSQL และ distributed locking
- Notification, PDF/Excel และ GPS

## Definition of Done

- Contract และ acceptance criteria ผ่าน
- `pytest` ผ่านทั้งหมด
- ไม่มี SQL รั่วเข้า views
- transaction boundary ถูกทดสอบ
- migration/schema change มีเอกสาร
- PR มี Frontend review เมื่อ contract เปลี่ยน
