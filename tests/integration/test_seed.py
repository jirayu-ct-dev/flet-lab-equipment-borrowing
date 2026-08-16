from collections import Counter

from app.database import connection
from app.seed import AUTH_SEED_KEY, DEMO_SEED_KEY, seed_demo_data
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
                "app_users",
            )
        }
        seed_runs = database.execute(
            "SELECT seed_key FROM app_seed_runs"
        ).fetchall()
        unit_statuses = Counter(
            row["status"]
            for row in database.execute("SELECT status FROM equipment_units")
        )
        users = [
            tuple(row)
            for row in database.execute(
                """
                SELECT email, role, staff_id, borrower_id, must_change_password
                FROM app_users
                ORDER BY id
                """
            )
        ]

    assert counts == {
        "equipment_categories": 9,
        "locations": 5,
        "staff": 3,
        "borrowers": 6,
        "equipment": 29,
        "equipment_units": 58,
        "borrow_transactions": 5,
        "borrow_items": 9,
        "returns": 5,
        "return_items": 5,
        "lost_cases": 1,
        "inventory_adjustments": 58,
        "app_users": 2,
    }
    assert sorted(row["seed_key"] for row in seed_runs) == sorted(
        [DEMO_SEED_KEY, AUTH_SEED_KEY]
    )
    assert unit_statuses == {
        "available": 52,
        "borrowed": 4,
        "maintenance": 1,
        "reported_lost": 1,
    }
    assert users == [
        ("admin@lab.local", "admin", 1, 6, 1),
        ("borrower@lab.local", "user", None, 1, 0),
    ]

    service = SQLiteInventoryAdapter(database_path)
    assert len(service.list_units()) == 58
    assert {loan.status for loan in service.list_loans()} == {"partial", "closed"}
    assert len(service.list_history()) >= 64
