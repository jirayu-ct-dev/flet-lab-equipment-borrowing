# Lab Equipment Borrowing System

เว็บแอปสำหรับจัดการการยืม–คืนอุปกรณ์ภายในห้องปฏิบัติการ พัฒนาด้วย
[Flet](https://flet.dev/) และ SQLite โดยเวอร์ชันแรกออกแบบให้เจ้าหน้าที่เป็นผู้ใช้งานหลัก
และยังไม่มีระบบเข้าสู่ระบบหลายระดับ

## ขอบเขต MVP

- จัดการข้อมูลอุปกรณ์และผู้ยืม
- บันทึกการยืมอุปกรณ์โดยตรวจสอบจำนวนพร้อมใช้
- บันทึกการคืนทั้งหมดหรือคืนบางส่วนได้หลายครั้ง
- แยกอุปกรณ์ที่คืนในสภาพชำรุดออกจากจำนวนพร้อมใช้
- ค้นหารายการที่กำลังยืมและรายการเกินกำหนด
- ดูประวัติการยืม–คืนย้อนหลัง
- จัดเก็บข้อมูลภายในเครื่องด้วย SQLite

รายละเอียด requirement, schema, business rules, user flow, acceptance criteria และลำดับการพัฒนาอยู่ใน
[แผนโครงการ](docs/project-plan.md)

## Tech Stack

- Python 3.11+
- Flet Web
- SQLite ผ่านโมดูล `sqlite3` ใน Python standard library
- `pytest` สำหรับ automated tests

เลือก `sqlite3` สำหรับ MVP เพื่อลด dependency และให้ transaction boundary ชัดเจน
หาก data model หรือ migration ซับซ้อนขึ้นจึงค่อยประเมิน ORM อีกครั้ง

## โครงสร้างโปรเจกต์เป้าหมาย

```text
flet-lab-equipment-borrowing/
├── main.py
├── requirements.txt
├── README.md
├── app/
│   ├── database.py
│   ├── models.py
│   ├── services/
│   └── views/
├── data/
├── docs/
│   └── project-plan.md
└── tests/
```

โครงสร้างนี้เป็นเป้าหมายระหว่างการพัฒนา ปัจจุบันอาจยังมีไฟล์ไม่ครบตามรายการ

## เริ่มต้นพัฒนา

เมื่อมี `requirements.txt` และ `main.py` แล้ว ให้ติดตั้งและเปิดแอปด้วยคำสั่ง:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
flet run --web main.py
```

บน Windows ให้ใช้ `.venv\Scripts\activate` แทนคำสั่ง activate ด้านบน

## การทดสอบ

เมื่อมี test suite แล้ว ให้รันด้วย:

```bash
python -m pytest
```

หัวใจของ test suite คือการยืนยันว่า transaction การยืม–คืนไม่ทำให้จำนวนอุปกรณ์ผิดพลาด
รวมถึงกรณียืมเกิน คืนเกิน คืนบางส่วนหลายครั้ง และเกิดข้อผิดพลาดระหว่างบันทึกข้อมูล

## สถานะโครงการ

อยู่ในขั้นวางแผน ยังไม่มี implementation สำหรับใช้งานจริง ดู milestone และเงื่อนไขความสำเร็จได้ใน
[docs/project-plan.md](docs/project-plan.md)

## License

โครงการนี้จัดทำขึ้นเพื่อการศึกษาและสามารถนำไปปรับปรุงต่อยอดได้
