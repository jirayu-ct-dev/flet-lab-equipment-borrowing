from collections import Counter

from app.database import connection
from app.seed import DEMO_SEED_KEY, seed_demo_data
from app.services.sqlite_adapter import SQLiteInventoryAdapter


def test_demo_seed_is_complete_and_idempotent(tmp_path) -> None:
    database_path = tmp_path / "demo-seed.db"

    assert seed_demo_data(database_path) is True
    assert seed_demo_data(database_path) is False

    with connection(database_path) as database:
        counts = {
            table: database.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "equipment_categories",
                "locations",
                "staff",
                "borrowers",
                "equipment",
                "equipment_units",
                "borrow_transactions",
                "borrow_items",
                "returns",
                "return_items",
                "lost_cases",
                "inventory_adjustments",
            )
        }
        seed_runs = database.execute(
            "SELECT seed_key FROM app_seed_runs"
        ).fetchall()
        unit_statuses = Counter(
            row["status"]
            for row in database.execute("SELECT status FROM equipment_units")
        )

    assert counts == {
        "equipment_categories": 8,
        "locations": 5,
        "staff": 3,
        "borrowers": 5,
        "equipment": 25,
        "equipment_units": 50,
        "borrow_transactions": 5,
        "borrow_items": 9,
        "returns": 5,
        "return_items": 5,
        "lost_cases": 1,
        "inventory_adjustments": 50,
    }
    assert [row["seed_key"] for row in seed_runs] == [DEMO_SEED_KEY]
    assert unit_statuses == {
        "available": 44,
        "borrowed": 4,
        "maintenance": 1,
        "reported_lost": 1,
    }

    service = SQLiteInventoryAdapter(database_path)
    assert len(service.list_units()) == 50
    assert {loan.status for loan in service.list_loans()} == {"partial", "closed"}
    assert len(service.list_history()) >= 64
