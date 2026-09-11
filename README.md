# ระบบยืม–คืนอุปกรณ์

Mini project สำหรับจัดการอุปกรณ์ได้หลายประเภท เช่น คอมพิวเตอร์ เครื่องมือ
วิทยาศาสตร์ โสตทัศนูปกรณ์ เครื่องมือช่าง และอุปกรณ์ทั่วไป ใช้งานผ่านเว็บและเก็บ
ข้อมูลใน SQLite บนเครื่องเดียว

## สิ่งที่ระบบทำได้

ระบบใช้แนวคิด “คิวงานก่อน” สำหรับเจ้าหน้าที่: เปิดหน้าแรกแล้วเห็นรายการที่ต้องคืน
วันนี้/เกินกำหนด พร้อมปุ่มยืมและรับคืนทันที ไม่ต้องไล่ผ่านฟอร์มหลายหน้าหรือจำรหัสเมนู

- ยืมหลายอุปกรณ์ในรายการเดียว โดยเลือกจากรายการที่พร้อมใช้งาน
- รับคืนโดยเลือกรายการ ระบบติ๊กอุปกรณ์ที่ยังค้างให้เอง และรองรับคืนบางส่วน
- แยกผลการคืนเป็นพร้อมใช้, ส่งซ่อม หรือแจ้งหาย พร้อมบันทึกจุดเก็บ/หมายเหตุ
- ค้นหาอุปกรณ์จากชื่อหรือ asset code และเห็นสถานะของแต่ละชิ้นชัดเจน
- จัดการผู้ยืม เจ้าหน้าที่ และบัญชีเข้าใช้จากหน้า “คนในระบบ” เดียว
- ดูรายการของฉัน, ประวัติย้อนหลัง และรายงานอุปกรณ์หาย
- เข้าระบบด้วยอีเมล/รหัสผ่านหรือ LINE Login
- ส่ง LINE แจ้งยืม/คืนและแจ้งเตือนกำหนดคืนเมื่อกำหนด Messaging API token
- ใช้วันที่ของระบบตามเขตเวลา `Asia/Bangkok` และเก็บ audit log แบบแก้ย้อนหลังไม่ได้

ระบบยังคงเป็นระบบขนาดเล็ก ใช้ SQLite บน volume เดียว ไม่ได้ทำ approval หลายขั้น,
QR scanner บังคับ, การชำระเงิน หรือการรองรับหลายสาขาพร้อมกัน

## เครื่องมือที่ต้องมี

เลือกใช้วิธีใดวิธีหนึ่ง:

- รันบนเครื่อง: Python 3.11 ขึ้นไป
- รันด้วย container: Docker Desktop หรือ Docker Engine

## วิธีรันบนเครื่อง

```text
บัญชี demo:
- ผู้ดูแลระบบ: admin@lab.local / admin123
- ผู้ยืม: borrower@lab.local / borrow123
```

เมื่อเข้าด้วยบัญชีผู้ดูแลครั้งแรก ระบบจะบังคับให้เปลี่ยนรหัสผ่าน

### macOS และ Linux

สร้าง virtual environment และติดตั้ง dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

เปิด Flet development server:

```bash
flet run --web --port 8550 main.py
```

เปิด [http://localhost:8550](http://localhost:8550) ในเบราว์เซอร์

### Windows Command Prompt

```bat
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
flet run --web --port 8550 main.py
```

เปิด [http://localhost:8550](http://localhost:8550) ในเบราว์เซอร์

### เพิ่มข้อมูลตัวอย่างโดยไม่ใช้ Docker

ข้อมูลตัวอย่างประกอบด้วยอุปกรณ์ 58 ชิ้น ผู้ยืม 6 คน รายการยืม 5 รายการ
รายการคืน 5 รายการ รวมถึงหมวดหมู่ สถานที่ เจ้าหน้าที่ ประวัติ ตัวอย่างส่งซ่อม
และตัวอย่างอุปกรณ์สูญหาย

macOS และ Linux:

```bash
APP_SEED_DEMO=1 flet run --web --port 8550 main.py
```

Windows Command Prompt:

```bat
set APP_SEED_DEMO=1
flet run --web --port 8550 main.py
```

ระบบจะเพิ่มข้อมูลตัวอย่างเพียงครั้งเดียวลง `data/lab_equipment.db` และไม่เพิ่มซ้ำ
เมื่อเริ่มโปรแกรมครั้งถัดไป หลังจาก seed สำเร็จสามารถกลับมารันคำสั่งปกติได้:

```bash
flet run --web --port 8550 main.py
```

หากต้องการสร้างชุดข้อมูลตัวอย่างใหม่ ให้ปิดโปรแกรมก่อน แล้วลบไฟล์
`data/lab_equipment.db` จากนั้นรันคำสั่งที่กำหนด `APP_SEED_DEMO=1` อีกครั้ง

## วิธีสร้างและรันด้วย Docker

### Docker Compose (แนะนำ)

สร้าง image และเปิด container โดยกำหนดพอร์ต `8080` ให้อัตโนมัติ:

```bash
docker compose up --build -d
```

หลังจากรันครั้งแรก Docker Desktop จะแสดง Compose app ชื่อ
`flet-lab-equipment-borrowing` ซึ่งสามารถกด Start/Stop ได้โดยไม่ต้องกำหนดพอร์ตใหม่

เปิด [http://localhost:8080](http://localhost:8080) ในเบราว์เซอร์

ข้อมูล SQLite ถูกเก็บไว้ที่ `./data/lab_equipment.db` และยังคงอยู่หลัง restart container

เมื่อ Docker เริ่มทำงาน ระบบจะเพิ่มข้อมูลตัวอย่างให้อัตโนมัติหนึ่งครั้ง ได้แก่
อุปกรณ์ 58 ชิ้น ผู้ยืม 6 คน รายการยืม 5 รายการ รายการคืน 5 รายการ รวมถึง
หมวดหมู่ สถานที่ เจ้าหน้าที่ ประวัติ และตัวอย่างอุปกรณ์สูญหาย ข้อมูลจะไม่ถูกเพิ่มซ้ำ
เมื่อ restart container

หากต้องการเริ่มฐานข้อมูลตัวอย่างใหม่ ให้หยุด container ก่อน แล้วลบไฟล์
`./data/lab_equipment.db` จากนั้นรัน `docker compose up --build -d` อีกครั้ง

หยุดและนำ container ออกด้วย:

```bash
docker compose down
```

### Docker image โดยตรง

สร้าง image จาก `Dockerfile`:

```bash
docker build -t lab-equipment-borrowing .
```

รัน container และเปิดพอร์ต `8080`:

```bash
docker run --rm --name lab-equipment-borrowing -p 8080:8080 lab-equipment-borrowing
```

เปิด [http://localhost:8080](http://localhost:8080) ในเบราว์เซอร์

หยุด container ด้วย `Ctrl+C` หากรันอยู่หน้า terminal หรือใช้คำสั่ง:

```bash
docker stop lab-equipment-borrowing
```

ชุดข้อมูลตัวอย่างถูกเปิดด้วยตัวแปร `APP_SEED_DEMO=1` ภายใน Docker image
หากต้องการเริ่ม container โดยไม่เพิ่มข้อมูลตัวอย่าง ให้กำหนด
`-e APP_SEED_DEMO=0` ตอนสั่ง `docker run`

## วิธีรันทดสอบ

ติดตั้ง development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

รัน test suite:

```bash
python -m pytest
```

## ตั้งค่า LINE

กำหนดค่าบนเครื่องหรือ Render/Docker environment เท่านั้น ห้าม commit ค่า secret:

```text
LINE_CLIENT_ID=...
LINE_CLIENT_SECRET=...
LINE_REDIRECT_URL=https://โดเมนของคุณ/
LINE_MESSAGING_CHANNEL_ACCESS_TOKEN=...
```

`LINE_REDIRECT_URL` ต้องเป็น URL เดียวกับที่ลงทะเบียนไว้ใน LINE Login channel
และต้องใช้ channel id/secret ชุดเดียวกัน ระบบจะสร้าง borrower profile ให้ LINE user
ใหม่โดยอัตโนมัติ เพื่อให้บัญชีไม่ค้างอยู่โดยไม่มีข้อมูลผู้ยืม; เจ้าหน้าที่แก้ชื่อ/หน่วยงาน
หรือเชื่อมกับข้อมูลเดิมได้จาก “คนในระบบ”

## เอกสารโครงการ

ขอบเขตและลำดับงานฉบับย่ออยู่ใน
[docs/project-plan.md](docs/project-plan.md)

เอกสารมอบหมายงานแยกตามทีม:

- [งาน Frontend](docs/scopes/frontend.md)
- [งาน Backend](docs/scopes/backend.md)
