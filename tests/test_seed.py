from app.seed import seed_render_demo
from app.service import AppService


def test_seed_render_demo_populates_a_blank_database_only_once(tmp_path):
    service = AppService(tmp_path / "app.db")

    assert seed_render_demo(service) is True
    assert len(service.list_users()) == 48
    assert len(service.list_units()) == 23
    assert len(service.list_master("category", active_only=True)) == 4
    assert seed_render_demo(service) is False
