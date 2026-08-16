"""ลงทะเบียน LINE Rich Menu ผ่าน Messaging API (แทนการกดใน Console)

วิธีใช้:
    1. กรอก LINE_MESSAGING_CHANNEL_ACCESS_TOKEN ใน .env
    2. รัน:  python scripts\\register_richmenus.py
    3. ก๊อป LINE_RICHMENU_ADMIN_ID / LINE_RICHMENU_USER_ID ไปใส่ใน .env

สคริปต์ลบ richmenu ชื่อซ้ำ (ตาม name ใน json) ก่อนสร้างใหม่ จึงรันซ้ำได้
อย่างปลอดภัย และแสดงรายการ richmenu ทั้งหมดเมื่อเสร็จ
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.env import load_env_file  # noqa: E402
from app.services.line_messaging import LINE_API_BASE, LineMessagingService  # noqa: E402

RICHMENUS = (
    {"key": "ADMIN", "name": "Admin Richmenu", "json": "json/admin.json", "image": "richmenuAdmin.jpg"},
    {"key": "USER", "name": "User Richmenu", "json": "json/user.json", "image": "richmenuUser.jpg"},
)


def _delete_existing(service: LineMessagingService, menu_name: str) -> None:
    from app.services.line_messaging import api_request

    body = api_request(
        "GET", f"{LINE_API_BASE}/v2/bot/richmenu/list", token=service.token
    )
    for menu in json.loads(body).get("richmenus", []):
        if menu.get("name") == menu_name:
            api_request(
                "DELETE",
                f"{LINE_API_BASE}/v2/bot/richmenu/{menu['richMenuId']}",
                token=service.token,
            )
            print(f"  ลบ richmenu เดิม: {menu_name} ({menu['richMenuId']})")


def register(script_dir: Path) -> dict[str, str]:
    from app.services.line_messaging import api_request

    service = LineMessagingService()
    if not service.is_configured():
        raise SystemExit(
            "ยังไม่ได้ตั้งค่า LINE_MESSAGING_CHANNEL_ACCESS_TOKEN ใน .env"
        )

    result: dict[str, str] = {}
    for menu in RICHMENUS:
        print(f"สร้าง richmenu: {menu['name']}")
        _delete_existing(service, menu["name"])

        payload = (script_dir / menu["json"]).read_text(encoding="utf-8")
        created = api_request(
            "POST",
            f"{LINE_API_BASE}/v2/bot/richmenu",
            token=service.token,
            body=payload.encode("utf-8"),
            content_type="application/json",
        )
        richmenu_id = json.loads(created)["richMenuId"]

        image = (script_dir / menu["image"]).read_bytes()
        api_request(
            "POST",
            f"{LINE_API_BASE}/v2/bot/richmenu/{richmenu_id}/content",
            token=service.token,
            body=image,
            content_type="image/jpeg",
        )
        print(f"  สำเร็จ: {richmenu_id}")
        result[menu["key"]] = richmenu_id

    return result


def main() -> None:
    load_env_file()
    script_dir = REPO_ROOT / "assets" / "richmenu"
    result = register(script_dir)

    print()
    print("ก๊อปบรรทัดนี้ไปใส่ใน .env:")
    print(f"LINE_RICHMENU_ADMIN_ID={result['ADMIN']}")
    print(f"LINE_RICHMENU_USER_ID={result['USER']}")


if __name__ == "__main__":
    main()
