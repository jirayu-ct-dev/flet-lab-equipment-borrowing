# แผนสลับ LINE Richmenu อัตโนมัติตาม Role

## 1. Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ ผู้ใช้เปิดแอป → กด "ล็อกอินด้วย LINE"                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ OAuth Flow:            │
        │ page.login(provider)   │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ on_line_authorized     │
        │ callback               │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ register_or_fetch_user │
        │ (สร้าง/ดึง user)      │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ ตรวจสอบ role          │
        │ (admin/user)           │
        └────────────┬───────────┘
                     │
            ┌────────┴────────┐
            │                 │
            ▼                 ▼
    ┌──────────────┐  ┌──────────────┐
    │ admin        │  │ user         │
    │              │  │              │
    └──────┬───────┘  └──────┬───────┘
           │                 │
           ▼                 ▼
  ┌───────────────┐  ┌───────────────┐
  │ Richmenu      │  │ Richmenu      │
  │ Admin         │  │ User          │
  └───────────────┘  └───────────────┘
```

## 2. Richmenu Mapping

| สถานะผู้ใช้ | Richmenu ID | ปุ่มหลัก |
|---|---|---|
| **admin** (เจ้าหน้าที่) | `admin_richmenu` | อุปกรณ์, คนในระบบ, ทำรายการยืม, คืนอุปกรณ์, ประวัติ, Dashboard |
| **user** (นักศึกษา/อาจารย์) | `user_richmenu` | อุปกรณ์, ของฉัน, ประวัติ, แจ้งหาย, คู่มือ, ติดต่อเจ้าหน้าที่ |

**หมายเหตุ:** ไม่มี "ผู้ใช้ใหม่" richmenu เพราะผู้ใช้ต้องล็อกอินผ่านแอปก่อน จึงจะเห็น richmenu

## 3. Code Structure

### 3.1 Richmenu Configuration

```python
# app/line_richmenu.py
import os

RICHMENU_IDS = {
    "admin": os.getenv("LINE_RICHMENU_ADMIN_ID"),
    "user": os.getenv("LINE_RICHMENU_USER_ID"),
}

def get_richmenu_for_user(user: AppUser | None) -> str | None:
    """เลือก richmenu ID ตาม role ของผู้ใช้"""
    if user is None:
        return None
    
    if user.role == Role.ADMIN:
        return RICHMENU_IDS["admin"]
    else:  # Role.USER
        return RICHMENU_IDS["user"]
```

### 3.2 LINE Messaging API Helper

```python
# app/services/line_messaging.py
import os
import requests

class LineMessagingService:
    def __init__(self):
        self.token = os.getenv("LINE_MESSAGING_CHANNEL_ACCESS_TOKEN")
        self.base_url = "https://api.line.me/v2/bot"
    
    def is_configured(self) -> bool:
        """เช็คว่า Messaging API ถูกตั้งค่าแล้ว"""
        return bool(self.token)
    
    def link_richmenu_to_user(self, user_id: str, richmenu_id: str) -> None:
        """เชื่อมโยง richmenu กับผู้ใช้"""
        if not self.is_configured() or not richmenu_id:
            return
        
        url = f"{self.base_url}/user/{user_id}/richmenu/{richmenu_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(url, headers=headers)
        response.raise_for_status()
    
    def unlink_richmenu_from_user(self, user_id: str) -> None:
        """ยกเลิก richmenu จากผู้ใช้"""
        if not self.is_configured():
            return
        
        url = f"{self.base_url}/user/{user_id}/richmenu"
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
```

### 3.3 สลับ Richmenu หลัง LINE Login

```python
# ใน main.py — on_line_authorized callback
def on_line_authorized(data: ft.LoginEvent) -> None:
    if data.error:
        _set_login_feedback("เข้าสู่ระบบด้วย LINE ไม่สำเร็จ กรุณาลองใหม่อีกครั้ง")
        return
    
    authorization = page.auth
    profile = (
        getattr(authorization, "user", None)
        if authorization is not None
        else None
    )
    if profile is None:
        _set_login_feedback("ไม่สามารถดึงข้อมูลผู้ใช้ LINE ได้ กรุณาลองใหม่อีกครั้ง")
        return
    
    display_name = profile.get("displayName") or "ผู้ใช้ LINE"
    user = register_or_fetch_user(auth, profile.id, display_name)
    
    # สลับ richmenu ตาม role
    line_service = LineMessagingService()
    richmenu_id = get_richmenu_for_user(user)
    if richmenu_id and user.line_sub:
        line_service.link_richmenu_to_user(user.line_sub, richmenu_id)
    
    handle_login_success(user)
```

### 3.4 เพิ่ม set_user_role ใน AuthService

```python
# app/contracts.py — เพิ่มใน AuthService protocol
@runtime_checkable
class AuthService(Protocol):
    # ... existing methods ...
    
    def set_user_role(self, user_id: int, new_role: Role, *, actor: AppUser) -> AppUser:
        """เปลี่ยน role ของผู้ใช้ (admin เท่านั้นที่ทำได้)"""
        ...
```

```python
# app/services/sqlite_auth_adapter.py
def set_user_role(self, user_id: int, new_role: Role, *, actor: AppUser) -> AppUser:
    if not has_permission(actor, Permission.MANAGE_USERS):
        raise PermissionDenied("ไม่มีสิทธิ์เปลี่ยน role ผู้ใช้")
    
    with connection(self.database_path) as database:
        database.execute(
            "UPDATE app_users SET role = ?, updated_at = ? WHERE id = ?",
            (new_role.value, utc_now().isoformat(timespec="milliseconds").replace("+00:00", "Z"), user_id)
        )
        database.commit()
    
    return self.get(user_id)
```

### 3.5 สลับ Richmenu เมื่อ Role เปลี่ยน

```python
# ใน Admin API หรือ UI handler
def update_user_role(user_id: int, new_role: Role, actor: AppUser) -> AppUser:
    """อัปเดต role และสลับ richmenu อัตโนมัติ"""
    # 1. อัปเดต role ในฐานข้อมูล
    user = auth_service.set_user_role(user_id, new_role, actor=actor)
    
    # 2. สลับ richmenu ถ้าผู้ใช้มี LINE account
    if user.line_sub:
        line_service = LineMessagingService()
        richmenu_id = get_richmenu_for_user(user)
        if richmenu_id:
            line_service.link_richmenu_to_user(user.line_sub, richmenu_id)
    
    return user
```

## 4. Edge Cases ที่ต้องจัดการ

| สถานการณ์ | การจัดการ |
|---|---|
| **LINE Login สำเร็จครั้งแรก** | เรียก `link_richmenu_to_user` ใน `on_line_authorized` |
| **LINE Login สำเร็จครั้งถัดไป** | เรียก `link_richmenu_to_user` อีกครั้ง (idempotent) |
| **Admin demote เป็น user** | เรียก `set_user_role` → สลับ richmenu |
| **User promote เป็น admin** | เรียก `set_user_role` → สลับ richmenu |
| **Messaging API ไม่ได้ตั้งค่า** | `LineMessagingService.is_configured()` return False → skip richmenu switching |
| **Richmenu ID ไม่ได้ตั้งค่าใน .env** | `get_richmenu_for_user` return None → skip |
| **ผู้ใช้ไม่มี LINE account** | `user.line_sub` is None → skip |
| **LINE API error** | Catch exception, log error, ไม่ block login flow |

## 5. Implementation Steps

1. **สร้าง richmenu images** (2 แบบ: admin, user) ขนาด 2500×1686
2. **Upload ไป LINE Developers Console** → ได้ richmenu ID
3. **ตั้งค่า tap areas** (coordinates) สำหรับแต่ละปุ่ม
4. **เพิ่ม env vars ใน `.env`:**
   - `LINE_MESSAGING_CHANNEL_ACCESS_TOKEN`
   - `LINE_RICHMENU_ADMIN_ID`
   - `LINE_RICHMENU_USER_ID`
5. **Implement `LineMessagingService`** (`app/services/line_messaging.py`)
6. **Implement `get_richmenu_for_user`** (`app/line_richmenu.py`)
7. **เพิ่ม `set_user_role` ใน `AuthService`** protocol + implementations
8. **เพิ่ม richmenu switching ใน `on_line_authorized`** (`main.py`)
9. **สร้าง Admin UI สำหรับเปลี่ยน role** (optional)
10. **Test**: LINE login → เห็น richmenu ตาม role → admin เปลี่ยน role → richmenu สลับ

## 6. ตัวอย่าง Flow จริง

```
1. นักศึกษาเปิดแอป → กด "ล็อกอินด้วย LINE"
   → OAuth flow → on_line_authorized
   → register_or_fetch_user (สร้าง user ใหม่ role=USER)
   → link_richmenu_to_user(user.line_sub, user_richmenu_id)
   → นักศึกษาเห็น richmenu: อุปกรณ์, ของฉัน, ประวัติ, ฯลฯ

2. Admin เปิดแอป → ล็อกอินด้วย LINE
   → on_line_authorized
   → register_or_fetch_user (ดึง user เดิม role=ADMIN)
   → link_richmenu_to_user(user.line_sub, admin_richmenu_id)
   → Admin เห็น richmenu: อุปกรณ์, คนในระบบ, ทำรายการยืม, ฯลฯ

3. Admin เปลี่ยน role นักศึกษาเป็นเจ้าหน้าที่ (ผ่าน Admin UI)
   → set_user_role(user_id, ADMIN, actor=admin)
   → link_richmenu_to_user(user.line_sub, admin_richmenu_id)
   → นักศึกษาเห็น richmenu ใหม่: อุปกรณ์, คนในระบบ, ฯลฯ

4. Admin demote กลับเป็นนักศึกษา
   → set_user_role(user_id, USER, actor=admin)
   → link_richmenu_to_user(user.line_sub, user_richmenu_id)
   → กลับไปเห็น richmenu เดิม
```

## 7. สิ่งที่ต้องทำเพิ่ม (ยังไม่ implement)

- [ ] `LineMessagingService` class (`app/services/line_messaging.py`)
- [ ] `get_richmenu_for_user` function (`app/line_richmenu.py`)
- [ ] `set_user_role` method ใน `AuthService` protocol + implementations
- [ ] Richmenu switching ใน `on_line_authorized` (`main.py`)
- [ ] Admin UI สำหรับเปลี่ยน role (optional)
- [ ] Error handling และ logging
- [ ] Env vars ใน `.env` และ `.env.example`

## 8. ข้อดีของแนวทางนี้

1. **ไม่ต้องเพิ่ม infrastructure** — ใช้ OAuth callback ที่มีอยู่แล้ว ไม่ต้องสร้าง webhook server
2. **ทำงานภายใน Flet architecture** — ไม่ต้องรัน Flask/Fastapi แยก
3. **Simple deployment** — แอปเดียวจบ ไม่ต้องจัดการหลาย services
4. **Idempotent** — เรียก `link_richmenu_to_user` หลายครั้งได้ปลอดภัย
5. **Graceful degradation** — ถ้า Messaging API ไม่ได้ตั้งค่า ระบบยังทำงานได้ (แค่ไม่สลับ richmenu)

## หมายเหตุ

- **Richmenu ID** ต้องสร้างจาก LINE Developers Console (upload image + set tap areas)
- **Messaging API channel** ต้องสร้างแยกจาก LINE Login channel
- **ไม่มี webhook** — ใช้ OAuth callback แทน (ง่ายกว่าและทำงานได้จริงใน Flet)
