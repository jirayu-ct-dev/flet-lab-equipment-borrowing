# แผน LINE Richmenu Routing

## 1. หลักการทำงาน

เมื่อผู้ใช้กดปุ่มบน richmenu → LINE จะเปิด URL ใน in-app browser → ผู้ใช้เห็นหน้าเว็บที่ตรงกับปุ่มนั้น

**สำคัญ:** ใช้ `uri` action (เปิด URL) แทน `postback` action เพราะไม่ต้องใช้ webhook

## 2. Admin Richmenu Routes

| ปุ่ม | Route | URL | หน้าที่แสดง |
|---|---|---|---|
| **อุปกรณ์** | `/inventory` | `https://<host>/inventory` | หน้ารายการอุปกรณ์ทั้งหมด |
| **คนในระบบ** | `/people` | `https://<host>/people` | หน้าจัดการ staff + borrowers |
| **ทำรายการยืม** | `/borrow` | `https://<host>/borrow` | หน้าสร้างรายการยืมใหม่ |
| **คืนอุปกรณ์** | `/returns` | `https://<host>/returns` | หน้าคืนอุปกรณ์ |
| **ประวัติ** | `/history` | `https://<host>/history` | หน้าดูประวัติทั้งหมด |
| **Dashboard** | `/dashboard` | `https://<host>/dashboard` | หน้า dashboard |

## 3. User Richmenu Routes

| ปุ่ม | Route | URL | หน้าที่แสดง |
|---|---|---|---|
| **อุปกรณ์** | `/inventory` | `https://<host>/inventory` | หน้ารายการอุปกรณ์ทั้งหมด |
| **ของฉัน** | `/my_loans` | `https://<host>/my_loans` | หน้ารายการยืมของตัวเอง |
| **ประวัติ** | `/history` | `https://<host>/history` | หน้าดูประวัติของตัวเอง |
| **แจ้งหาย** | `/report_lost` | `https://<host>/report_lost` | หน้าแจ้งอุปกรณ์หาย |
| **คู่มือ** | `/guide` | `https://<host>/guide` | หน้าคู่มือการใช้งาน |
| **ติดต่อเจ้าหน้าที่** | `/contact` | `https://<host>/contact` | หน้าข้อมูลติดต่อ |

## 4. Richmenu Configuration (JSON)

### 4.1 Admin Richmenu

```json
{
  "size": {
    "width": 2500,
    "height": 1686
  },
  "selected": false,
  "name": "Admin Richmenu",
  "chatBarText": "เมนูผู้ดูแล",
  "areas": [
    {
      "bounds": {"x": 0, "y": 0, "width": 833, "height": 843},
      "action": {
        "type": "uri",
        "uri": "https://<host>/inventory"
      }
    },
    {
      "bounds": {"x": 833, "y": 0, "width": 833, "height": 843},
      "action": {
        "type": "uri",
        "uri": "https://<host>/people"
      }
    },
    {
      "bounds": {"x": 1666, "y": 0, "width": 834, "height": 843},
      "action": {
        "type": "uri",
        "uri": "https://<host>/borrow"
      }
    },
    {
      "bounds": {"x": 0, "y": 843, "width": 833, "height": 843},
      "action": {
        "type": "uri",
        "uri": "https://<host>/returns"
      }
    },
    {
      "bounds": {"x": 833, "y": 843, "width": 833, "height": 843},
      "action": {
        "type": "uri",
        "uri": "https://<host>/history"
      }
    },
    {
      "bounds": {"x": 1666, "y": 843, "width": 834, "height": 843},
      "action": {
        "type": "uri",
        "uri": "https://<host>/dashboard"
      }
    }
  ]
}
```

### 4.2 User Richmenu

```json
{
  "size": {
    "width": 2500,
    "height": 1686
  },
  "selected": false,
  "name": "User Richmenu",
  "chatBarText": "เมนู",
  "areas": [
    {
      "bounds": {"x": 0, "y": 0, "width": 833, "height": 843},
      "action": {
        "type": "uri",
        "uri": "https://<host>/inventory"
      }
    },
    {
      "bounds": {"x": 833, "y": 0, "width": 833, "height": 843},
      "action": {
        "type": "uri",
        "uri": "https://<host>/my_loans"
      }
    },
    {
      "bounds": {"x": 1666, "y": 0, "width": 834, "height": 843},
      "action": {
        "type": "uri",
        "uri": "https://<host>/history"
      }
    },
    {
      "bounds": {"x": 0, "y": 843, "width": 833, "height": 843},
      "action": {
        "type": "uri",
        "uri": "https://<host>/report_lost"
      }
    },
    {
      "bounds": {"x": 833, "y": 843, "width": 833, "height": 843},
      "action": {
        "type": "uri",
        "uri": "https://<host>/guide"
      }
    },
    {
      "bounds": {"x": 1666, "y": 843, "width": 834, "height": 843},
      "action": {
        "type": "uri",
        "uri": "https://<host>/contact"
      }
    }
  ]
}
```

## 5. Authentication Flow

เมื่อผู้ใช้กดปุ่ม richmenu → เปิด URL ใน LINE in-app browser:

```
1. ผู้ใช้กดปุ่ม "ของฉัน" ใน richmenu
   → LINE เปิด https://<host>/my_loans
   
2. Flet app ตรวจสอบ session
   → ถ้ามี session → แสดงหน้า my_loans
   → ถ้าไม่มี session → redirect ไปหน้า login
   
3. ผู้ใช้ล็อกอิน (email/password หรือ LINE)
   → สร้าง session
   → redirect กลับไปหน้า /my_loans
   
4. แสดงหน้า my_loans
```

**หมายเหตุ:** Flet จัดการ routing อัตโนมัติผ่าน `page.route` และ `page.on_route_change`

## 6. Routes ที่ต้องสร้างเพิ่ม

| Route | สถานะ | คำอธิบาย |
|---|---|---|
| `/inventory` | ✅ มีแล้ว | หน้าอุปกรณ์ |
| `/people` | ✅ มีแล้ว | หน้าคนในระบบ |
| `/borrow` | ✅ มีแล้ว | หน้าทำรายการยืม |
| `/returns` | ✅ มีแล้ว | หน้าคืนอุปกรณ์ |
| `/history` | ✅ มีแล้ว | หน้าประวัติ |
| `/dashboard` | ✅ มีแล้ว | หน้า dashboard |
| `/my_loans` | ✅ มีแล้ว | หน้าของฉัน |
| `/report_lost` | ❌ ยังไม่มี | หน้าแจ้งอุปกรณ์หาย (ต้องสร้าง) |
| `/guide` | ❌ ยังไม่มี | หน้าคู่มือ (ต้องสร้าง) |
| `/contact` | ❌ ยังไม่มี | หน้าติดต่อเจ้าหน้าที่ (ต้องสร้าง) |

## 7. Implementation Steps

1. **สร้างหน้าที่ขาด:**
   - `app/views/report_lost.py` — ฟอร์มแจ้งอุปกรณ์หาย
   - `app/views/guide.py` — คู่มือการใช้งาน
   - `app/views/contact.py` — ข้อมูลติดต่อเจ้าหน้าที่

2. **เพิ่ม routes ใน `main.py`:**
   ```python
   elif route == "/report_lost":
       content_area.content = build_screen(ReportLostView(service, current_user=current_user))
   elif route == "/guide":
       content_area.content = build_screen(GuideView())
   elif route == "/contact":
       content_area.content = build_screen(ContactView())
   ```

3. **Upload richmenu JSON ไป LINE Console:**
   - ใช้ LINE Messaging API: `POST https://api.line.me/v2/bot/richmenu`
   - Upload image: `POST https://api.line.me/v2/bot/richmenu/{richmenuId}/content`

4. **ทดสอบ:**
   - กดปุ่ม richmenu → เปิด URL ถูกต้อง
   - ล็อกอิน → เห็นหน้าที่ถูกต้อง
   - Logout → กดปุ่ม → redirect ไป login

## 8. Edge Cases

| สถานการณ์ | การจัดการ |
|---|---|
| **ผู้ใช้กดปุ่มแต่ยังไม่ได้ล็อกอิน** | Redirect ไปหน้า login → ล็อกอินเสร็จ → redirect กลับ |
| **ผู้ใช้ไม่มีสิทธิ์เข้าหน้า** (เช่น user กด /people) | แสดงข้อความ "ไม่มีสิทธิ์เข้าถึง" |
| **URL ไม่ถูกต้อง** | แสดง 404 page |
| **LINE in-app browser ปิด JavaScript** | Flet ไม่ทำงาน → แสดงข้อความ "กรุณาเปิด JavaScript" |

## 9. ตัวอย่าง Flow จริง

```
1. นักศึกษาเปิด LINE → เห็น richmenu "เมนู"
   → กด "ของฉัน"
   → LINE เปิด https://bru-cs.example.com/my_loans
   
2. Flet app ตรวจสอบ session
   → ไม่มี session → redirect ไป /login
   
3. นักศึกษากด "ล็อกอินด้วย LINE"
   → OAuth flow → สร้าง session
   → redirect กลับไป /my_loans
   
4. แสดงหน้า "ของฉัน"
   → เห็นรายการยืมของตัวเอง
   → เห็นวันครบกำหนดคืน
```

## 10. ข้อดีของแนวทางนี้

1. **ไม่ต้องใช้ webhook** — ใช้ `uri` action เปิด URL โดยตรง
2. **ทำงานกับ Flet routing** — ใช้ `page.route` ที่มีอยู่แล้ว
3. **Deep linking** — ผู้ใช้เข้าถึงหน้าเฉพาะได้ทันทีจาก richmenu
4. **Authentication ทำงานอัตโนมัติ** — Flet จัดการ session + redirect
5. **Simple implementation** — แค่เพิ่ม routes + views ที่ขาด

## หมายเหตุ

- **Routes ที่มีอยู่แล้ว** (inventory, people, borrow, returns, history, dashboard, my_loans) ไม่ต้องสร้างใหม่
- **Routes ที่ต้องสร้าง** (report_lost, guide, contact) เป็นหน้า static/form ง่ายๆ
- **Richmenu bounds** คำนวณจาก 2500/3 = 833.33 → ใช้ 833, 833, 834 เพื่อให้ครบ 2500
