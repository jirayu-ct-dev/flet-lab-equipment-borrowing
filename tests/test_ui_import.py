import flet as ft

import app.ui as ui_module
from app.ui import AppUI


class DialogPage:
    def __init__(self) -> None:
        self.dialogs = []

    def show_dialog(self, dialog) -> None:
        self.dialogs.append(dialog)


def test_import_dialog_uses_browser_client_action() -> None:
    page = DialogPage()
    ui = AppUI.__new__(AppUI)
    ui.page = page
    original_handler = lambda _: None
    ui.file_picker = ft.FilePicker(on_result=original_handler)

    ui.import_users_dialog()

    dialog = page.dialogs[0]
    content = dialog.content.content.controls
    assert len(content) == 2
    assert isinstance(content[1], ft.OutlinedButton)
    assert content[1].content == "ดาวน์โหลดไฟล์ตัวอย่าง (.xlsx)"
    pick_button = dialog.actions[-1]
    assert isinstance(pick_button.action, ft.PickFiles)
    assert pick_button.action.file_picker is ui.file_picker
    assert pick_button.action.allowed_extensions == ["csv", "xlsx"]
    assert pick_button.action.with_data is True
    assert ui.file_picker.on_result is original_handler


def test_import_file_selection_normalizes_web_file_bytes(monkeypatch) -> None:
    ui = AppUI.__new__(AppUI)
    ui.service = object()
    ui.pending_import = None
    calls = []
    ui.close_dialog = lambda: calls.append("closed")
    ui.import_preview_dialog = lambda: calls.append("previewed")
    ui.feedback = lambda message, error=False: calls.append((message, error))

    expected_preview = object()

    def preview_users(service, name, data):
        assert service is ui.service
        assert name == "users.xlsx"
        assert data == b"workbook"
        return expected_preview

    monkeypatch.setattr(ui_module, "preview_users", preview_users)
    event = ft.FilePickerResultEvent(
        name="result",
        control=ft.FilePicker(),
        files=[ft.FilePickerFile(1, "users.xlsx", 8, bytes=list(b"workbook"))],
    )

    ui._handle_import_file_selected(event)

    assert ui.pending_import is expected_preview
    assert calls == ["closed", "previewed"]
