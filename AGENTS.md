# AGENTS.md

## Project

Flet Web + SQLite MVP สำหรับยืม–คืนอุปกรณ์ของสาขาวิทยาการคอมพิวเตอร์ เอกสารหลักคือ `docs/project_scope.md`; เมื่อเอกสารเก่าหรือสมมติฐานอื่นขัดกัน ให้ยึด scope นี้

UI copy เป็นภาษาไทย ส่วนชื่อในโค้ดและสถานะในฐานข้อมูลเป็นภาษาอังกฤษ

## Commands

```bash
python -m pip install -r requirements-dev.txt
flet run --web --port 8550 main.py
python -m pytest
python -m compileall -q main.py app
```

## Architecture

- `main.py` โหลด `.env` และเริ่ม `AppUI`
- `app/ui.py` เป็น Flet shell และหน้าจอทั้งหมดของ Admin/ผู้ยืม
- `app/service.py` เป็น boundary เดียวของกฎธุรกิจและคำสั่ง SQLite ไม่มี repository abstraction หรือ fake service
- `app/database.py` เป็น schema และการเปิด connection; default DB คือ `data/equipment_lending.db` แบบยึด project root
- `app/import_users.py` อ่าน/ตรวจ/นำเข้า CSV และ XLSX
- `app/line.py` มี LINE OAuth provider และ text push client แบบ best effort
- `app/security.py` เก็บ PBKDF2 password hashing

## Domain rules

- มี role แค่ `admin` และ `borrower`; user type คือ `student`, `teacher`, `staff`
- username ไม่ซ้ำแบบ case-insensitive และเป็นรหัสผ่านเริ่มต้นของผู้ใช้ใหม่
- DB ใหม่สร้าง `admin` / `admin1234` ครั้งเดียวและบังคับเปลี่ยนรหัส
- การสร้าง loan และเปลี่ยน unit เป็น `borrowed` ต้องอยู่ transaction เดียวกัน
- การคืนบันทึกที่ `loan_items.returned_at`; partial return ได้ และ loan ปิดเมื่อครบทุกชิ้น
- ผู้ยืม inactive หรือมีรายการเกินกำหนดยืมเพิ่มไม่ได้
- ใช้ `Asia/Bangkok` สำหรับ business date และ UTC `Z` สำหรับ timestamp
- LINE ส่งแบบ best effort ห้ามทำให้ loan/return rollback
- ข้อมูลที่มีประวัติใช้ inactive แทน delete

## Tests

ใช้ SQLite file ใน `tmp_path` เท่านั้น ห้ามแตะฐานข้อมูลจริง ทดสอบกฎที่ public service seam และ mock เฉพาะ network/time boundary เมื่อจำเป็น

## UI

เน้น search-first, ปุ่มงานหลักชัด, confirmation ก่อน mutation สำคัญ และสถานะต้องมีข้อความร่วมกับสี ห้ามกำหนด `expand=False` ใน Flet 0.86; ใช้ `None` เมื่อไม่ต้องการ flex และอย่าใช้ flex child ภายใน `Row(wrap=True)`
