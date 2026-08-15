# AGENTS.md

## Project: flet-lab-equipment-borrowing

Flet (Python) web app for a lab-equipment borrowing system. SQLite backend, single
user, no auth. **All UI copy is Thai** (labels, hints, toasts); domain code and
status strings are English.

### Commands

```bash
python -m pip install -r requirements-dev.txt   # deps: flet + pytest only (no lint/format config in repo)
flet run --web --port 8550 main.py              # dev server; entrypoint is repo-root main.py
python -m pytest                                # full suite; no pytest config, no conftest
docker compose up --build -d                    # → http://localhost:8080
```

- Demo data: set `APP_SEED_DEMO=1` (Docker sets it by default). Seeding is idempotent
  via the `app_seed_runs` table (`app/seed.py`); delete `data/lab_equipment.db` to reseed.
- DB location: `APP_DB_PATH` env var; default is the relative `data/lab_equipment.db`.
  Under `flet run`, the process CWD is `.flet/storage/data` (see `.flet/README.md`), so
  the relative default lands elsewhere — set `APP_DB_PATH` for a predictable location.

### Architecture & wiring

- `main.py` builds the app shell and swaps `content_area.content` per nav tab; views in
  `app/views/`.
- Views consume one duck-typed service facade: `FakeInventoryService` (in-memory,
  `app/services/fake_services.py`) or `SQLiteInventoryAdapter` (persistent,
  `app/services/sqlite_adapter.py`), chosen by `create_app_services()`
  (`app/services/container.py`). **Keep the fake and SQLite implementations in sync** —
  changing one's API almost always means updating the other plus its tests.
- Domain layer: `app/contracts.py` (dataclasses + runtime-checkable Protocols),
  `app/repositories/` (raw SQL), `app/services/*.py` (domain logic), `app/errors.py`
  (`DomainError` hierarchy the UI maps to user feedback).
- Migrations are the `MIGRATIONS` tuple in `app/database.py`; `initialize_database()`
  applies pending versions (tracked in `schema_migrations`). To add a migration, append
  to the tuple — existing DBs must upgrade in place. `audit_logs` is append-only (triggers).
- Times are persisted as UTC ISO strings ending in `Z`; calendar dates derive from
  `Asia/Bangkok` via `bangkok_today()`/`bangkok_date()`. Never compare business dates
  against raw timestamps.
- Flet 0.86 layout gotcha: **never assign `expand = False`** — it corrupts the whole
  enclosing `Row`/`ResponsiveRow` (renders as two full-height panels). Use
  `expand = None` to un-flex. Guarded by `tests/test_layout_guards.py`; debugging
  playbook in `.agents/skills/flet-layout-debug/SKILL.md`.

### Testing

- `tests/` = view + fake-service unit tests (build flet controls, assert structure; no
  server needed). `tests/integration/` = SQLite/migration/seed/service tests using
  `tmp_path` DBs — never touch the real `data/`.
- `tests/integration/test_seed.py` asserts exact demo row counts (50 units, 5 loans, ...);
  update it when seed data changes.
- Status strings are English in the domain (`available`, `borrowed`, ...); Thai display
  labels live in `STATUS_THEMES` in `app/theme.py`.

---

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
