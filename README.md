# Lab Equipment Borrowing System

Flet Web foundation สำหรับระบบยืม–คืนอุปกรณ์ห้องปฏิบัติการ

## เครื่องมือที่ต้องมี

เลือกใช้วิธีใดวิธีหนึ่ง:

- รันบนเครื่อง: Python 3.11 ขึ้นไป
- รันด้วย container: Docker Desktop หรือ Docker Engine

## วิธีรันบนเครื่อง

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

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
flet run --web --port 8550 main.py
```

เปิด [http://localhost:8550](http://localhost:8550) ในเบราว์เซอร์

## วิธีสร้างและรันด้วย Docker

### Docker Compose (แนะนำ)

สร้าง image และเปิด container โดยกำหนดพอร์ต `8080` ให้อัตโนมัติ:

```bash
docker compose up --build -d
```

หลังจากรันครั้งแรก Docker Desktop จะแสดง Compose app ชื่อ
`flet-lab-equipment-borrowing` ซึ่งสามารถกด Start/Stop ได้โดยไม่ต้องกำหนดพอร์ตใหม่

เปิด [http://localhost:8080](http://localhost:8080) ในเบราว์เซอร์

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

## วิธีรันทดสอบ

ติดตั้ง development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

รัน test suite:

```bash
python -m pytest
```

## เอกสารโครงการ

รายละเอียดขอบเขต, data model, business rules และแผนพัฒนาอยู่ใน
[docs/project-plan.md](docs/project-plan.md)

เอกสารมอบหมายงานแยกตามทีม:

- [Frontend Scope](docs/scopes/frontend.md)
- [Backend Scope](docs/scopes/backend.md)
