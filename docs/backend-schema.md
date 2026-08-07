# Backend database schema and migrations

The Backend uses SQLite. The database file is selected from `APP_DB_PATH`; when the
variable is not set, the default is `data/lab_equipment.db`.

`app.database.initialize_database()` applies pending migrations in version order.
Applied versions are stored in `schema_migrations`, so initialization is safe to run
more than once. Every connection enables `PRAGMA foreign_keys = ON`.

## Time representation

- Event timestamps are stored as UTC ISO 8601 strings ending in `Z`.
- Business dates are stored as ISO dates (`YYYY-MM-DD`).
- Due-date queries derive the current business date in `Asia/Bangkok` from an
  injectable backend clock.

## Migration history

### Version 1 — Initial schema

Creates the following tables:

- `locations`
- `equipment`
- `equipment_units`
- `staff`
- `borrowers`
- `borrow_transactions`
- `borrow_items`
- `returns`
- `return_items`
- `lost_cases`
- `inventory_adjustments`
- `audit_logs`

The migration includes foreign keys, unique business and asset codes, non-negative
amount checks, lifecycle status checks, due-date validation, one return per borrow
item, and one lost case per borrow item.

### Version 2 — Return location history

Adds nullable `return_items.location_id` referencing `locations.id`. Normal and
maintenance returns require this value at the service boundary. Reported-lost items
leave it null.

### Version 3 — Replacement identity

Adds nullable `lost_cases.replacement_unit_id` referencing `equipment_units.id`.
The original lost unit remains a separate record; a replacement resolution creates
a new unit and stores its identifier here.

### Version 4 — Append-only audit log

Adds `audit_logs_no_update` and `audit_logs_no_delete` triggers. SQLite rejects
updates and deletes with `audit logs are append-only`; new audit entries remain
insertable.

## Transaction boundaries

The following operations use a single `BEGIN IMMEDIATE` transaction and roll back
as a unit on failure:

- acquiring, relocating, retiring, and completing repair of a unit;
- confirming a multi-unit loan;
- recording a return event and all its items;
- opening and resolving a lost case, including replacement creation;
- editing loan details, changing borrower, and replacing a loan unit;
- appending the audit entry associated with lost resolution and loan-edit actions.

SQLite conditional updates and the unit lifecycle state prevent two confirmed loans
from claiming the same available unit. Integration tests use real temporary SQLite
files and include concurrent and injected-failure cases.

## Adding a migration

1. Append a new SQL script to `MIGRATIONS` in `app/database.py`; never reorder or
   modify a migration that may already have been applied.
2. Document the new version and compatibility impact in this file.
3. Add an integration test covering initialization, repeat initialization, relevant
   constraints, and upgrade behavior.
4. If DTOs or service signatures change, request Frontend review before merge.
