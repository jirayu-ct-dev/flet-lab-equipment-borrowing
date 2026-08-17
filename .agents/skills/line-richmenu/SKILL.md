---
name: line-richmenu
description: Add, update, verify, and fix LINE Rich Menus for this app entirely through the LINE Messaging API (no Console clicks). Use this skill when a user wants to register/change richmenus, make one the default, or debug LINE richmenu errors (400/404). It provides ready-to-run commands: register all menus, verify live state, resize images to the exact LINE-required 2500x1686, set a default menu, and a bug-fix playbook keyed by exact error message. Key rules: image upload goes to api-data.line.me (not api.line.me), images must be exactly 2500x1686 under 1MB, the create payload's "selected" field is REQUIRED (send false) but selected:true is deprecated so the default must be set via POST /v2/bot/user/all/richmenu/{id} AFTER the image upload, and Windows console needs PYTHONIOENCODING=utf-8 for Thai output.
---

# LINE Rich Menu

Three richmenus in this channel: `New User` (channel default for users who
never logged in), `Admin` and `User` (linked per logged-in user by role via
`sync_richmenu` in `main.py` → `app/line_richmenu.py`). Everything below talks
to LINE directly — no Console.

Files you will touch:
- `scripts/register_richmenus.py` — the register script (source of truth)
- `assets/richmenu/json/{new-user,admin,user}.json` — menu payloads
- `assets/richmenu/{richmenuNewUser,richmenuAdmin,richmenuUser}.jpg` — images
- `.env` — `LINE_RICHMENU_ADMIN_ID` / `LINE_RICHMENU_USER_ID` (IDs change
  every run — always refresh after registering)
- `app/services/line_messaging.py` — `api_request`, `LineMessagingService`

## Run: register all menus (add/update richmenus)

```powershell
$env:PYTHONIOENCODING="utf-8"; python scripts\register_richmenus.py
```

What it does: for each entry in `RICHMENUS`, delete any menu with the same
`name`, create it, upload its image, and for `"key": "NEW_USER"` set it as the
channel default. Then prints new IDs — **copy them into `.env`** and update
`LINE_RICHMENU_ADMIN_ID` / `LINE_RICHMENU_USER_ID`.

To add a NEW menu: add an entry to the `RICHMENUS` tuple in
`register_richmenus.py` plus a JSON under `assets/richmenu/json/` and an image;
give it `"key": "NEW_USER"` only if it should become the channel default.

## Verify live state

```python
import json
from app.env import load_env_file
from app.services.line_messaging import api_request, LineMessagingService, LINE_API_BASE
load_env_file()
svc = LineMessagingService()
menus = json.loads(api_request("GET", f"{LINE_API_BASE}/v2/bot/richmenu/list", token=svc.token))
default = json.loads(api_request("GET", f"{LINE_API_BASE}/v2/bot/user/all/richmenu", token=svc.token))
print([(m["name"], m["richMenuId"], m["selected"]) for m in menus["richmenus"]])
print("default:", default.get("richMenuId"))
```

Check: 3 menus listed, `default` == New User richmenu, and both `.env` IDs
appear in the list.

## Fix playbook (keyed by exact error)

### 400 `"must upload richmenu image before applying it to user"`
The set-default call ran **before** the image upload. In `register_richmenus.py`
the order must be: create → upload image → THEN `POST /v2/bot/user/all/richmenu/{id}`.
Move the default-set block after the upload block.

### 400 `{"message":"must be specified","property":"selected"}` on create
The payload JSON is missing `selected` — it is a REQUIRED field. Add
`"selected": false` to the JSON (default is set by the endpoint, not by this
field).

### 400 on image upload (`/content`)
Two causes:
1. Wrong host: content upload must go to `api-data.line.me`
   (`LINE_API_DATA_BASE`), not `api.line.me`.
2. Wrong image size: must be exactly one of `2500x1686`, `2500x843`,
   `1200x810`, `1200x405`, `800x540`, `800x270`, and under 1MB. Resize:

```python
from PIL import Image
im = Image.open("assets/richmenu/richmenuAdmin.jpg").convert("RGB")
im = im.resize((2500, 1686), Image.LANCZOS)   # exact required dims
im.save("assets/richmenu/richmenuAdmin.jpg", "JPEG", quality=92)
```

### 404 `"no default richmenu"` from `GET /v2/bot/user/all/richmenu`
Expected when no default is set — does NOT mean the token is broken. Set the
default (must have uploaded the image first):

```python
from app.env import load_env_file
from app.services.line_messaging import api_request, LineMessagingService, LINE_API_BASE
load_env_file()
svc = LineMessagingService()
api_request("POST", f"{LINE_API_BASE}/v2/bot/user/all/richmenu/{richmenu_id}", token=svc.token, body=b"")
```

### `UnicodeEncodeError: 'charmap'` on Windows
Thai output vs cp1252 console. Always prefix:
`$env:PYTHONIOENCODING="utf-8"; python ...`

## Rule reminders (do not rediscover these)

1. Upload host = `api-data.line.me`; everything else = `api.line.me`.
2. Image must be exact LINE-valid size (2500x1686) and < 1MB.
3. `selected` is required in create payload → send `false`.
4. `selected:true` is deprecated — default is set ONLY via
   `POST /v2/bot/user/all/richmenu/{id}` and only AFTER image upload.
5. Every successful register run produces new IDs → update `.env`.

## Secrets

The token in `.env` is real and long-lived. The Postman collection
(`assets/richmenu/Richmenu.postman_collection.json`) once contained real
secrets and was committed in `eb6dbce`; it is now git-ignored
(`assets/richmenu/*.postman_collection.json`) and untracked. Rotate the token
in the LINE Console if it appears in git history. Never echo the token value.

## Tests

- `tests/test_line_richmenu.py` — role→ID mapping; full suite: `python -m pytest`.