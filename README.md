# Flet Lab Equipment Lending

ระบบยืม–คืนอุปกรณ์ของสาขาวิทยาการคอมพิวเตอร์ ใช้ Python, Flet Web และ SQLite

ขอบเขตที่อนุมัติอยู่ที่ [docs/project_scope.md](docs/project_scope.md) ระบบนี้ตั้งใจให้เป็น MVP สำหรับโปรเจกต์ในวิชา จึงไม่มีคำขอยืม การจอง การอนุมัติหลายขั้น ชำรุด สูญหาย ค่าปรับ audit log หรือ production deployment

## เริ่มใช้งาน

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
flet run --web --port 8550 main.py
```

เปิด <http://localhost:8550>

ฐานข้อมูลใหม่จะสร้างบัญชีแรกเพียงบัญชีเดียว:

- Username: `admin`
- Password: `admin1234`
- ระบบบังคับเปลี่ยนรหัสผ่านก่อนใช้งาน

ฐานข้อมูลเริ่มต้นอยู่ที่ `data/equipment_lending.db` แบบ absolute path จาก project root จึงไม่เปลี่ยนตำแหน่งเมื่อรันผ่าน Flet สามารถกำหนดไฟล์อื่นด้วย `APP_DB_PATH` ได้

## LINE

คัดลอก `.env.example` เป็น `.env` แล้วกำหนด:

```env
LINE_CLIENT_ID=
LINE_CLIENT_SECRET=
LINE_REDIRECT_URL=http://localhost:8550/oauth_callback
LINE_MESSAGING_CHANNEL_ACCESS_TOKEN=
```

LINE Login และ Messaging API ต้องอยู่ Provider เดียวกัน ผู้ใช้ LINE ครั้งแรกต้องยืนยัน username/password ของระบบก่อนผูกบัญชี และต้องเพิ่ม Official Account เป็นเพื่อนจึงจะรับข้อความได้

## ทดสอบ

```bash
python -m pytest
python -m compileall -q main.py app
```

ไม่มี Docker, PostgreSQL, lint หรือ typecheck configuration ในขอบเขต MVP นี้
