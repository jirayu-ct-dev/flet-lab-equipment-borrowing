# LINE Richmenu Assets

ไฟล์รูปและ config สำหรับ LINE Richmenu

## รูปภาพ (2500x1686 px)

| ไฟล์ | ใช้กับ | คำอธิบาย |
|---|---|---|
| `richmenuAdmin.jpg` | admin (เจ้าหน้าที่) | 6 ปุ่ม: อุปกรณ์, คนในระบบ, ทำรายการยืม, คืนอุปกรณ์, ประวัติ, Dashboard |
| `richmenuUser.jpg` | user (นักศึกษา/อาจารย์) | 6 ปุ่ม: อุปกรณ์, ของฉัน, ประวัติ, แจ้งหาย, คู่มือ, ติดต่อเจ้าหน้าที่ |
| `richmenuNewUser.jpg` | ผู้ใช้ใหม่ | 6 ปุ่ม: เกี่ยวกับระบบ, ลงทะเบียน, เข้าสู่ระบบ, คู่มือ, FAQ, ติดต่อเจ้าหน้าที่ |
| `profile.jpg` | LINE Profile | รูปโปรไฟล์ของ LINE Official Account |

## JSON Configs (`json/`)

| ไฟล์ | ใช้กับรูป | tap areas |
|---|---|---|
| `json/admin.json` | `richmenuAdmin.jpg` | 3×2 grid, uri actions |
| `json/user.json` | `richmenuUser.jpg` | 3×2 grid, uri actions |
| `json/new-user.json` | `richmenuNewUser.jpg` | 3×2 grid, uri actions |

## วิธีใช้

1. แทนที่ `<host>` ใน JSON ด้วย URL จริง เช่น `bru-cs.example.com`
2. Upload richmenu ผ่าน LINE Messaging API:

```bash
# สร้าง richmenu
curl -X POST https://api.line.me/v2/bot/richmenu \
  -H "Authorization: Bearer <CHANNEL_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d @json/admin.json

# Upload รูป
curl -X POST https://api.line.me/v2/bot/richmenu/{richmenuId}/content \
  -H "Authorization: Bearer <CHANNEL_ACCESS_TOKEN>" \
  -H "Content-Type: image/jpeg" \
  -T richmenuAdmin.jpg
```

3. อัปเดต `LINE_RICHMENU_ADMIN_ID` / `LINE_RICHMENU_USER_ID` ใน `.env`

## ดูแผนเพิ่มเติม

- `docs/line-richmenu-plan.md` — แผนสลับ richmenu อัตโนมัติตาม role
- `docs/line-richmenu-routing.md` — แผน routing จากปุ่ม richmenu ไปหน้าเว็บ
