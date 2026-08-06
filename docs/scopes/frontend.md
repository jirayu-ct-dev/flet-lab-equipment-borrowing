# Frontend Scope

## เป้าหมาย

สร้าง Flet Web UI สำหรับเจ้าหน้าที่ให้ทำงานตาม user flow ได้ครบ โดยเรียก domain services
ผ่าน contract กลางและไม่เข้าถึง SQLite โดยตรง

## Ownership

Frontend เป็น owner ของ:

```text
main.py
app/views/
app/components/
app/theme.py
tests/ui/
```

Frontend ร่วม review `app/models.py` หรือ `app/contracts.py` แต่ไม่เขียน SQL ใน view
และไม่แก้ database schema โดยไม่ผ่าน Backend review

## งานตามลำดับ

### FE-01 — App shell และ design foundation

- Navigation สำหรับ Inventory, Staff, Borrowers, Loans และ History
- theme, spacing, typography และ responsive content area
- reusable loading, empty, error และ confirmation states
- current staff selector สำหรับ MVP ที่ยังไม่มี login

**Acceptance:** navigation ใช้ได้ทั้งจอกว้างและแคบ และทุกหน้ามี loading/empty/error state

### FE-02 — Fake services

- implement fake services ตาม Backend contract
- เตรียม fixture สำหรับ available, borrowed, maintenance, lost และ retired units
- ห้ามสร้าง model ซ้ำใน views

**Acceptance:** หน้าจอพัฒนาและ demo ได้ก่อน SQLite services เสร็จ และสลับ implementation ได้จาก composition root

### FE-03 — Inventory screens

- รายการ/ค้นหา equipment types และ units
- เพิ่ม/แก้ equipment type
- เพิ่ม unit พร้อม asset code, serial, ราคา และตำแหน่ง
- relocate, retire และ repair-complete actions พร้อมเหตุผล

**Acceptance:** แสดงสถานะและตำแหน่งล่าสุดชัดเจน และ validation errors ผูกกับ field ที่เกี่ยวข้อง

### FE-04 — Staff และ Borrower screens

- เพิ่ม แก้ ค้นหา และ inactive records
- ไม่แสดง inactive staff ใน selector สำหรับรายการใหม่
- ยังค้นเจอ inactive records ใน history

**Acceptance:** forms ป้องกัน submit ซ้ำและแสดง duplicate code error

### FE-05 — Borrow flow

- เลือก borrower, staff และ available units
- ระบุ borrow/due dates, purpose และ note
- review summary ก่อน confirm
- แสดง stale/not-available error โดยไม่ทำข้อมูลใน form หาย

**Acceptance:** ยืนยัน loan หลาย unit ได้และ refresh แล้วเห็น units เป็น borrowed

### FE-06 — Active loans และ return flow

- filter due today, due soon, overdue และ partial
- เลือกคืนบาง unit
- ระบุ outcome/condition ต่อ unit
- confirmation และผลลัพธ์หลังบันทึก

**Acceptance:** คืนบางส่วนหลายครั้งได้ และ maintenance/lost ไม่แสดงเป็น available

### FE-07 — Lost resolution และ edits

- lost case detail พร้อม assessed/approved value
- recovered, replaced, compensated และ waived forms
- due date/purpose/note edit พร้อม required reason
- แสดง audit timeline แบบ read-only

**Acceptance:** UI ไม่อนุญาต resolve โดยข้อมูลผู้อนุมัติไม่ครบ และแสดงประวัติการแก้ไขได้

### FE-08 — History และ usability

- ค้นหาจาก borrower, equipment, asset code และช่วงวันที่
- แสดง loan, return events, lost resolution และ audit entries ตามลำดับเวลา
- responsive และ keyboard-friendly forms

**Acceptance:** ผู้ใช้ตามรอย unit หนึ่งชิ้นตั้งแต่รับเข้า ยืม คืน/สูญหาย จนปิดรายการได้

## Contract usage rules

- View รับ services ผ่าน constructor/composition root
- View ไม่ import repository, connection หรือ `sqlite3`
- Domain errors ถูก map เป็นข้อความผู้ใช้ในชั้น UI
- ห้ามคำนวณ overdue จากเวลา browser; ใช้ค่าที่ query service ส่งมา
- ห้ามแก้ model fields โดยตรงแล้วถือว่าบันทึกสำเร็จ ต้องเรียก command method

## Test requirements

- unit test สำหรับ state/validation ที่สำคัญ
- UI smoke tests สำหรับ navigation และ forms หลัก
- manual responsive check อย่างน้อย desktop และ mobile width
- integration demo ใช้ SQLite service ก่อน merge milestone

## ไม่อยู่ในขอบเขต Frontend MVP

- Login/permissions UI
- Dashboard analytics
- QR scanner, notification, reports และ GPS
- custom design system ขนาดใหญ่หรือ animation ที่ไม่ช่วย workflow

## Definition of Done

- ตรง acceptance criteria และใช้ service contract
- ไม่มี SQL/database import ใน views
- loading, empty, success และ error states ครบ
- ป้องกัน double submit
- responsive check ผ่าน
- tests ผ่านและ PR ได้ Backend review เมื่อ contract usage เปลี่ยน
