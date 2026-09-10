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

### Authentication & authorization

- Roles: `admin` (staff, full access) / `user` (borrower self-service: อุปกรณ์, ของฉัน,
  ประวัติ). `Role`, `Permission`, `ROLE_PERMISSIONS`, `has_permission()` live in
  `app/contracts.py`; both roles are enforced in TWO places: nav/route gating in
  `main.py` (`visible_navigation_items` + `navigate_to` guard) and
  `if not has_permission(...)` guards at the top of every mutation handler in views
  (`borrow_flow`, `loans`, `staff_borrowers`, `dashboard`).
- Identity: `app_users` (email + password_hash via `app/security.py` pbkdf2, and/or
  LINE via `line_sub`) linking to `staff_id` or `borrower_id`. `AuthService` protocol
  implemented by `FakeAuthService` and `SQLiteAuthAdapter` — keep them in sync like
  the inventory facades.
- Session: `page.session["user_id"]`; `main()` shows LoginView or the shell;
  `must_change_password` routes to ChangePasswordView. LINE login uses flet's
  `page.login(OAuthProvider)` (`app/services/line_login.py`), enabled by env vars
  `LINE_CLIENT_ID` / `LINE_CLIENT_SECRET` / `LINE_REDIRECT_URL` — never commit secrets.
- Demo accounts (seeded): `admin@lab.local`/`admin123` (must change on first login),
  `borrower@lab.local`/`borrow123`. Test fixtures: `tests/test_auth_fixtures.py`.

### Testing

- `tests/` = view + fake-service unit tests (build flet controls, assert structure; no
  server needed). `tests/integration/` = SQLite/migration/seed/service tests using
  `tmp_path` DBs — never touch the real `data/`.
- `tests/integration/test_seed.py` asserts exact demo row counts (50 units, 5 loans, ...);
  update it when seed data changes.
- Status strings are English in the domain (`available`, `borrowed`, ...); Thai display
  labels live in `STATUS_THEMES` in `app/theme.py`.

---

General operating principles for coding agents. Apply them across projects, then adapt to this repository's instructions, conventions, and tooling.

**Balance:** Favor correctness and restraint without turning low-risk work into ceremony. For small, reversible tasks, inspect briefly and proceed. For ambiguous, high-impact, or destructive work, slow down and confirm the important assumptions.

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## Scope and authority

**The request defines the goal; it does not authorize unrelated work.**

- For explanation, review, or diagnosis, inspect and report. Do not modify unless asked.
- For implementation or fixes, make the necessary in-scope changes and verify them.
- Ask before material destructive operations that were not explicitly requested, adding major dependencies, changing public contracts, or expanding scope materially.
- Follow explicit repository requirements and the most specific applicable project instructions; surface conflicts instead of silently choosing.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- Read relevant code, nearby documentation, and applicable `AGENTS.md` files.
- Identify the requested outcome, current behavior, and constraints; check project conventions and available commands instead of guessing.
- Consider whether a smaller solution already exists in the repository.
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

## Adapt to the project

- Use repository documentation and package scripts to discover build, test, lint, and formatting commands.
- Put language-, framework-, or domain-specific workflows in the relevant local instructions or skills, not in this general guidance.
- Prefer formatters, linters, type checkers, tests, and CI for rules that can be checked mechanically.
- Do not replace an established project pattern merely because another pattern is generally preferred.

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

During implementation, reproduce bugs before fixing them when practical, add or update tests when behavior changes and the project has a suitable test structure, run the narrowest relevant checks first, and review the final diff for accidental scope expansion.

At handoff, state what changed, what was verified, and any remaining uncertainty. Never claim a check passed if it was not run.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
