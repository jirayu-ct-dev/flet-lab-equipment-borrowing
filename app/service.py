from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from app.database import bangkok_today, connect, initialize_database, utc_now, utc_text
from app.errors import AuthenticationError, NotFoundError, PermissionDenied, ValidationError
from app.models import LineMessage, User
from app.security import hash_password, hash_session_token, new_session_token, validate_password_strength, verify_password


USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,50}$")
MASTER_TABLES = {
    "faculty": ("faculties", None),
    "department": ("departments", "faculty_id"),
    "cohort": ("cohorts", "department_id"),
    "class_group": ("class_groups", "cohort_id"),
    "category": ("equipment_categories", None),
}
SESSION_LIFETIME = timedelta(days=30)


class AppService:
    """กฎธุรกิจและ SQLite boundary เดียวของ MVP"""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = initialize_database(path)

    @staticmethod
    def _user(row: sqlite3.Row | None) -> User | None:
        if row is None:
            return None
        return User(
            id=row["id"],
            username=row["username"],
            full_name=row["full_name"],
            role=row["role"],
            user_type=row["user_type"],
            status=row["status"],
            must_change_password=bool(row["must_change_password"]),
            backup_email=row["backup_email"],
            faculty_id=row["faculty_id"],
            department_id=row["department_id"],
            cohort_id=row["cohort_id"],
            class_group_id=row["class_group_id"],
            line_user_id=row["line_user_id"],
        )

    def get_user(self, user_id: int | None) -> User | None:
        if not user_id:
            return None
        with connect(self.path) as db:
            return self._user(db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())

    def create_session(self, user_id: int) -> str:
        token = new_session_token()
        now = utc_now()
        with connect(self.path) as db:
            db.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (utc_text(now),))
            db.execute(
                "INSERT INTO auth_sessions(token_hash, user_id, expires_at, last_used_at) VALUES (?, ?, ?, ?)",
                (hash_session_token(token), user_id, utc_text(now + SESSION_LIFETIME), utc_text(now)),
            )
            db.commit()
        return token

    def user_for_session(self, token: str | None) -> User | None:
        if not token:
            return None
        now = utc_text()
        with connect(self.path) as db:
            row = db.execute(
                """SELECT u.* FROM auth_sessions AS s
                   JOIN users AS u ON u.id = s.user_id
                   WHERE s.token_hash = ? AND s.expires_at > ? AND u.status = 'active'""",
                (hash_session_token(token), now),
            ).fetchone()
            if row is None:
                return None
            db.execute("UPDATE auth_sessions SET last_used_at = ? WHERE token_hash = ?", (now, hash_session_token(token)))
            db.commit()
            return self._user(row)

    def revoke_session(self, token: str | None) -> None:
        if not token:
            return
        with connect(self.path) as db:
            db.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (hash_session_token(token),))
            db.commit()

    @staticmethod
    def _revoke_user_sessions(db: sqlite3.Connection, user_id: int) -> None:
        db.execute("DELETE FROM auth_sessions WHERE user_id = ?", (user_id,))

    def authenticate(self, username: str, password: str) -> User:
        with connect(self.path) as db:
            row = db.execute(
                "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
                (username.strip(),),
            ).fetchone()
            if row is None or not verify_password(password, row["password_hash"]):
                raise AuthenticationError("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
            if row["status"] != "active":
                raise AuthenticationError("บัญชีนี้ถูกปิดใช้งาน")
            db.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (utc_text(), row["id"]))
            db.commit()
            return self._user(row)  # type: ignore[return-value]

    def change_password(self, user_id: int, current_password: str, new_password: str) -> User:
        error = validate_password_strength(new_password)
        if error:
            raise ValidationError(error)
        with connect(self.path) as db:
            row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if row is None:
                raise NotFoundError("ไม่พบบัญชีผู้ใช้")
            if not verify_password(current_password, row["password_hash"]):
                raise AuthenticationError("รหัสผ่านปัจจุบันไม่ถูกต้อง")
            db.execute(
                "UPDATE users SET password_hash = ?, must_change_password = 0, updated_at = ? WHERE id = ?",
                (hash_password(new_password), utc_text(), user_id),
            )
            self._revoke_user_sessions(db, user_id)
            db.commit()
        return self.get_user(user_id)  # type: ignore[return-value]

    def _require_admin(self, db: sqlite3.Connection, actor_id: int) -> sqlite3.Row:
        actor = db.execute("SELECT * FROM users WHERE id = ?", (actor_id,)).fetchone()
        if actor is None or actor["status"] != "active" or actor["role"] != "admin":
            raise PermissionDenied("เฉพาะผู้ดูแลระบบเท่านั้น")
        return actor

    @staticmethod
    def _validate_username(username: str) -> str:
        value = username.strip()
        if not USERNAME_RE.fullmatch(value):
            raise ValidationError("ชื่อผู้ใช้ต้องยาว 3–50 ตัว และใช้ได้เฉพาะ a-z, A-Z, 0-9, จุด, ขีดล่าง และขีดกลาง")
        return value

    def _validate_user_fields(
        self,
        db: sqlite3.Connection,
        *,
        role: str,
        user_type: str,
        faculty_id: int | None,
        department_id: int | None,
        cohort_id: int | None,
        class_group_id: int | None,
    ) -> int | None:
        if role not in {"admin", "borrower"}:
            raise ValidationError("บทบาทไม่ถูกต้อง")
        if user_type not in {"student", "teacher", "staff"}:
            raise ValidationError("ประเภทผู้ใช้ไม่ถูกต้อง")
        if role == "admin":
            return class_group_id
        if faculty_id is None or department_id is None:
            raise ValidationError("กรุณาระบุคณะและสาขา")
        department = db.execute(
            "SELECT id FROM departments WHERE id = ? AND faculty_id = ? AND status = 'active'",
            (department_id, faculty_id),
        ).fetchone()
        if department is None:
            raise ValidationError("คณะและสาขาไม่สัมพันธ์กันหรือถูกปิดใช้งาน")
        if user_type != "student":
            return None
        if cohort_id is None:
            raise ValidationError("นักศึกษาต้องระบุรุ่น")
        cohort = db.execute(
            "SELECT id FROM cohorts WHERE id = ? AND department_id = ? AND status = 'active'",
            (cohort_id, department_id),
        ).fetchone()
        if cohort is None:
            raise ValidationError("รุ่นไม่สัมพันธ์กับสาขาหรือถูกปิดใช้งาน")
        groups = db.execute(
            "SELECT id FROM class_groups WHERE cohort_id = ? AND status = 'active' ORDER BY name",
            (cohort_id,),
        ).fetchall()
        if len(groups) > 1 and class_group_id is None:
            raise ValidationError("รุ่นนี้มีหลายหมู่เรียน กรุณาระบุหมู่เรียน")
        if len(groups) == 1 and class_group_id is None:
            return groups[0]["id"]
        if class_group_id is not None and class_group_id not in {row["id"] for row in groups}:
            raise ValidationError("หมู่เรียนไม่สัมพันธ์กับรุ่นหรือถูกปิดใช้งาน")
        return class_group_id

    def save_user(
        self,
        actor_id: int,
        *,
        username: str,
        full_name: str,
        role: str = "borrower",
        user_type: str = "student",
        backup_email: str | None = None,
        faculty_id: int | None = None,
        department_id: int | None = None,
        cohort_id: int | None = None,
        class_group_id: int | None = None,
        user_id: int | None = None,
    ) -> User:
        username = self._validate_username(username)
        full_name = full_name.strip()
        if not full_name:
            raise ValidationError("กรุณาระบุชื่อ–นามสกุล")
        with connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_admin(db, actor_id)
            class_group_id = self._validate_user_fields(
                db,
                role=role,
                user_type=user_type,
                faculty_id=faculty_id,
                department_id=department_id,
                cohort_id=cohort_id,
                class_group_id=class_group_id,
            )
            try:
                if user_id is None:
                    cursor = db.execute(
                        """
                        INSERT INTO users(
                            username, password_hash, full_name, backup_email, role,
                            user_type, faculty_id, department_id, cohort_id,
                            class_group_id, must_change_password
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                        """,
                        (
                            username,
                            hash_password(username),
                            full_name,
                            backup_email or None,
                            role,
                            user_type,
                            faculty_id,
                            department_id,
                            cohort_id if user_type == "student" else None,
                            class_group_id if user_type == "student" else None,
                        ),
                    )
                    user_id = cursor.lastrowid
                else:
                    if db.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
                        raise NotFoundError("ไม่พบบัญชีผู้ใช้")
                    db.execute(
                        """
                        UPDATE users SET username = ?, full_name = ?, backup_email = ?,
                            role = ?, user_type = ?, faculty_id = ?, department_id = ?,
                            cohort_id = ?, class_group_id = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            username,
                            full_name,
                            backup_email or None,
                            role,
                            user_type,
                            faculty_id,
                            department_id,
                            cohort_id if user_type == "student" else None,
                            class_group_id if user_type == "student" else None,
                            utc_text(),
                            user_id,
                        ),
                    )
                db.commit()
            except sqlite3.IntegrityError as error:
                db.rollback()
                if "users.username" in str(error):
                    raise ValidationError("ชื่อผู้ใช้นี้มีอยู่แล้ว") from error
                raise ValidationError("บันทึกผู้ใช้ไม่สำเร็จ กรุณาตรวจข้อมูลที่ซ้ำกัน") from error
        return self.get_user(user_id)  # type: ignore[arg-type,return-value]

    def list_users(self, query: str = "", status: str | None = None) -> list[sqlite3.Row]:
        where = ["1 = 1"]
        values: list[object] = []
        if query.strip():
            where.append("(u.username LIKE ? OR u.full_name LIKE ?)")
            term = f"%{query.strip()}%"
            values.extend((term, term))
        if status in {"active", "inactive"}:
            where.append("u.status = ?")
            values.append(status)
        with connect(self.path) as db:
            return db.execute(
                f"""
                SELECT u.*, f.name AS faculty_name, d.name AS department_name,
                       c.name AS cohort_name, g.name AS class_group_name
                FROM users u
                LEFT JOIN faculties f ON f.id = u.faculty_id
                LEFT JOIN departments d ON d.id = u.department_id
                LEFT JOIN cohorts c ON c.id = u.cohort_id
                LEFT JOIN class_groups g ON g.id = u.class_group_id
                WHERE {' AND '.join(where)}
                ORDER BY u.full_name COLLATE NOCASE
                """,
                values,
            ).fetchall()

    def set_user_status(self, actor_id: int, user_id: int, status: str) -> None:
        if status not in {"active", "inactive"}:
            raise ValidationError("สถานะไม่ถูกต้อง")
        with connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_admin(db, actor_id)
            target = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if target is None:
                raise NotFoundError("ไม่พบบัญชีผู้ใช้")
            if actor_id == user_id and status == "inactive":
                raise ValidationError("ไม่สามารถปิดบัญชีที่กำลังใช้งานอยู่")
            if target["role"] == "admin" and status == "inactive":
                active_admins = db.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND status = 'active'").fetchone()[0]
                if active_admins <= 1:
                    raise ValidationError("ต้องมีผู้ดูแลที่ใช้งานได้อย่างน้อยหนึ่งบัญชี")
            db.execute("UPDATE users SET status = ?, updated_at = ? WHERE id = ?", (status, utc_text(), user_id))
            db.commit()

    def reset_password(self, actor_id: int, user_id: int) -> str:
        with connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_admin(db, actor_id)
            row = db.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
            if row is None:
                raise NotFoundError("ไม่พบบัญชีผู้ใช้")
            password = row["username"]
            db.execute(
                "UPDATE users SET password_hash = ?, must_change_password = 1, updated_at = ? WHERE id = ?",
                (hash_password(password), utc_text(), user_id),
            )
            self._revoke_user_sessions(db, user_id)
            db.commit()
            return password

    def find_by_line(self, line_user_id: str) -> User | None:
        with connect(self.path) as db:
            row = db.execute("SELECT * FROM users WHERE line_user_id = ?", (line_user_id,)).fetchone()
            user = self._user(row)
            return user if user and user.status == "active" else None

    def link_line(self, username: str, password: str, line_user_id: str) -> User:
        user = self.authenticate(username, password)
        if user.line_user_id and user.line_user_id != line_user_id:
            raise ValidationError("บัญชีระบบนี้ผูก LINE อื่นอยู่ กรุณายกเลิกการเชื่อมเดิมก่อน")
        with connect(self.path) as db:
            try:
                db.execute("UPDATE users SET line_user_id = ?, updated_at = ? WHERE id = ?", (line_user_id, utc_text(), user.id))
                db.commit()
            except sqlite3.IntegrityError as error:
                raise ValidationError("บัญชี LINE นี้ผูกกับผู้ใช้อื่นแล้ว") from error
        return self.get_user(user.id)  # type: ignore[return-value]

    def unlink_line(self, user_id: int) -> None:
        with connect(self.path) as db:
            db.execute("UPDATE users SET line_user_id = NULL, updated_at = ? WHERE id = ?", (utc_text(), user_id))
            db.commit()

    def list_master(self, kind: str, *, active_only: bool = False) -> list[sqlite3.Row]:
        if kind not in MASTER_TABLES:
            raise ValidationError("ชนิดข้อมูลหลักไม่ถูกต้อง")
        table, parent_column = MASTER_TABLES[kind]
        where = "WHERE x.status = 'active'" if active_only else ""
        join = ""
        parent_name = "NULL AS parent_name"
        if kind == "department":
            join, parent_name = "JOIN faculties p ON p.id = x.faculty_id", "p.name AS parent_name"
        elif kind == "cohort":
            join, parent_name = "JOIN departments p ON p.id = x.department_id", "p.name AS parent_name"
        elif kind == "class_group":
            join, parent_name = "JOIN cohorts p ON p.id = x.cohort_id", "p.name AS parent_name"
        with connect(self.path) as db:
            return db.execute(
                f"SELECT x.*, {parent_name} FROM {table} x {join} {where} ORDER BY x.name COLLATE NOCASE"
            ).fetchall()

    def save_master(
        self,
        actor_id: int,
        kind: str,
        name: str,
        *,
        parent_id: int | None = None,
        record_id: int | None = None,
    ) -> int:
        if kind not in MASTER_TABLES:
            raise ValidationError("ชนิดข้อมูลหลักไม่ถูกต้อง")
        table, parent_column = MASTER_TABLES[kind]
        name = name.strip()
        if not name:
            raise ValidationError("กรุณาระบุชื่อ")
        if parent_column and parent_id is None:
            raise ValidationError("กรุณาเลือกข้อมูลแม่")
        with connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_admin(db, actor_id)
            if parent_column:
                parent_table = {
                    "faculty_id": "faculties",
                    "department_id": "departments",
                    "cohort_id": "cohorts",
                }[parent_column]
                if db.execute(
                    f"SELECT 1 FROM {parent_table} WHERE id = ? AND status = 'active'",
                    (parent_id,),
                ).fetchone() is None:
                    raise ValidationError("ข้อมูลแม่ไม่มีอยู่หรือถูกปิดใช้งาน")
            try:
                if record_id is None:
                    columns = f"name, {parent_column}" if parent_column else "name"
                    marks = "?, ?" if parent_column else "?"
                    values = (name, parent_id) if parent_column else (name,)
                    record_id = db.execute(f"INSERT INTO {table}({columns}) VALUES ({marks})", values).lastrowid
                else:
                    values = (name, parent_id, record_id) if parent_column else (name, record_id)
                    assignment = f"name = ?, {parent_column} = ?" if parent_column else "name = ?"
                    if db.execute(f"UPDATE {table} SET {assignment} WHERE id = ?", values).rowcount != 1:
                        raise NotFoundError("ไม่พบข้อมูลหลัก")
                db.commit()
            except sqlite3.IntegrityError as error:
                db.rollback()
                raise ValidationError("ชื่อนี้มีอยู่แล้วในรายการเดียวกัน") from error
        return int(record_id)

    def set_master_status(self, actor_id: int, kind: str, record_id: int, status: str) -> None:
        if kind not in MASTER_TABLES or status not in {"active", "inactive"}:
            raise ValidationError("ข้อมูลหรือสถานะไม่ถูกต้อง")
        table = MASTER_TABLES[kind][0]
        with connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_admin(db, actor_id)
            if db.execute(f"UPDATE {table} SET status = ? WHERE id = ?", (status, record_id)).rowcount != 1:
                raise NotFoundError("ไม่พบข้อมูลหลัก")
            db.commit()

    def save_equipment_type(
        self,
        actor_id: int,
        *,
        name: str,
        category_id: int,
        brand: str = "",
        model: str = "",
        description: str = "",
        type_id: int | None = None,
    ) -> int:
        if not name.strip():
            raise ValidationError("กรุณาระบุชื่อชนิดอุปกรณ์")
        with connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_admin(db, actor_id)
            category = db.execute("SELECT 1 FROM equipment_categories WHERE id = ? AND status = 'active'", (category_id,)).fetchone()
            if category is None:
                raise ValidationError("กรุณาเลือกหมวดหมู่ที่ใช้งานอยู่")
            try:
                if type_id is None:
                    type_id = db.execute(
                        "INSERT INTO equipment_types(name, category_id, brand, model, description) VALUES (?, ?, ?, ?, ?)",
                        (name.strip(), category_id, brand.strip() or None, model.strip() or None, description.strip() or None),
                    ).lastrowid
                else:
                    if db.execute(
                        "UPDATE equipment_types SET name = ?, category_id = ?, brand = ?, model = ?, description = ?, updated_at = ? WHERE id = ?",
                        (name.strip(), category_id, brand.strip() or None, model.strip() or None, description.strip() or None, utc_text(), type_id),
                    ).rowcount != 1:
                        raise NotFoundError("ไม่พบชนิดอุปกรณ์")
                db.commit()
            except sqlite3.IntegrityError as error:
                raise ValidationError("ชนิดอุปกรณ์นี้มีอยู่แล้ว") from error
        return int(type_id)

    def list_equipment_types(self, query: str = "", *, active_only: bool = False) -> list[sqlite3.Row]:
        where = []
        values: list[object] = []
        if active_only:
            where.append("t.status = 'active'")
        if query.strip():
            where.append("(t.name LIKE ? OR t.brand LIKE ? OR t.model LIKE ?)")
            term = f"%{query.strip()}%"
            values.extend((term, term, term))
        clause = "WHERE " + " AND ".join(where) if where else ""
        with connect(self.path) as db:
            return db.execute(
                f"""SELECT t.*, c.name AS category_name,
                    (SELECT COUNT(*) FROM equipment_units u WHERE u.equipment_type_id = t.id) AS unit_count
                    FROM equipment_types t JOIN equipment_categories c ON c.id = t.category_id
                    {clause} ORDER BY t.name COLLATE NOCASE""",
                values,
            ).fetchall()

    def set_equipment_type_status(self, actor_id: int, type_id: int, status: str) -> None:
        if status not in {"active", "inactive"}:
            raise ValidationError("สถานะไม่ถูกต้อง")
        with connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_admin(db, actor_id)
            if status == "inactive" and db.execute(
                "SELECT 1 FROM equipment_units WHERE equipment_type_id = ? AND status = 'borrowed'", (type_id,)
            ).fetchone():
                raise ValidationError("ปิดชนิดอุปกรณ์ไม่ได้ขณะที่มีชิ้นที่กำลังถูกยืม")
            if db.execute("UPDATE equipment_types SET status = ?, updated_at = ? WHERE id = ?", (status, utc_text(), type_id)).rowcount != 1:
                raise NotFoundError("ไม่พบชนิดอุปกรณ์")
            db.commit()

    def save_unit(
        self,
        actor_id: int,
        *,
        equipment_type_id: int,
        asset_code: str,
        storage_location: str,
        unit_id: int | None = None,
    ) -> int:
        asset_code = asset_code.strip()
        storage_location = storage_location.strip()
        if not asset_code or not storage_location:
            raise ValidationError("กรุณาระบุ asset code และตำแหน่งจัดเก็บ")
        with connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_admin(db, actor_id)
            if db.execute("SELECT 1 FROM equipment_types WHERE id = ? AND status = 'active'", (equipment_type_id,)).fetchone() is None:
                raise ValidationError("กรุณาเลือกชนิดอุปกรณ์ที่ใช้งานอยู่")
            try:
                if unit_id is None:
                    unit_id = db.execute(
                        "INSERT INTO equipment_units(equipment_type_id, asset_code, storage_location) VALUES (?, ?, ?)",
                        (equipment_type_id, asset_code, storage_location),
                    ).lastrowid
                else:
                    row = db.execute("SELECT status FROM equipment_units WHERE id = ?", (unit_id,)).fetchone()
                    if row is None:
                        raise NotFoundError("ไม่พบอุปกรณ์รายชิ้น")
                    db.execute(
                        "UPDATE equipment_units SET equipment_type_id = ?, asset_code = ?, storage_location = ?, updated_at = ? WHERE id = ?",
                        (equipment_type_id, asset_code, storage_location, utc_text(), unit_id),
                    )
                db.commit()
            except sqlite3.IntegrityError as error:
                raise ValidationError("asset code นี้มีอยู่แล้ว") from error
        return int(unit_id)

    def set_unit_status(self, actor_id: int, unit_id: int, status: str) -> None:
        if status not in {"available", "inactive"}:
            raise ValidationError("สถานะไม่ถูกต้อง")
        with connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_admin(db, actor_id)
            row = db.execute("SELECT status FROM equipment_units WHERE id = ?", (unit_id,)).fetchone()
            if row is None:
                raise NotFoundError("ไม่พบอุปกรณ์รายชิ้น")
            if row["status"] == "borrowed":
                raise ValidationError("เปลี่ยนสถานะอุปกรณ์ที่กำลังถูกยืมไม่ได้")
            db.execute("UPDATE equipment_units SET status = ?, updated_at = ? WHERE id = ?", (status, utc_text(), unit_id))
            db.commit()

    def list_units(self, query: str = "", status: str | None = None) -> list[sqlite3.Row]:
        where = ["1 = 1"]
        values: list[object] = []
        if query.strip():
            term = f"%{query.strip()}%"
            where.append("(u.asset_code LIKE ? OR t.name LIKE ? OR t.brand LIKE ? OR t.model LIKE ? OR u.storage_location LIKE ?)")
            values.extend((term, term, term, term, term))
        if status in {"available", "borrowed", "inactive"}:
            where.append("u.status = ?")
            values.append(status)
        if status == "available":
            where.append("t.status = 'active'")
        with connect(self.path) as db:
            return db.execute(
                f"""SELECT u.*, t.name AS type_name, t.brand, t.model, c.name AS category_name
                    FROM equipment_units u
                    JOIN equipment_types t ON t.id = u.equipment_type_id
                    JOIN equipment_categories c ON c.id = t.category_id
                    WHERE {' AND '.join(where)} ORDER BY u.asset_code COLLATE NOCASE""",
                values,
            ).fetchall()

    def create_loan(
        self,
        actor_id: int,
        borrower_id: int,
        unit_ids: list[int],
        borrow_date: date,
        due_date: date,
    ) -> sqlite3.Row:
        if due_date < borrow_date:
            raise ValidationError("วันครบกำหนดต้องไม่ก่อนวันยืม")
        if not unit_ids:
            raise ValidationError("กรุณาเลือกอุปกรณ์อย่างน้อยหนึ่งชิ้น")
        if len(unit_ids) != len(set(unit_ids)):
            raise ValidationError("มีอุปกรณ์ซ้ำในรายการ")
        with connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_admin(db, actor_id)
            borrower = db.execute("SELECT * FROM users WHERE id = ?", (borrower_id,)).fetchone()
            if borrower is None or borrower["role"] != "borrower" or borrower["status"] != "active":
                raise ValidationError("ผู้ยืมไม่พร้อมใช้งาน")
            overdue = db.execute(
                """SELECT 1 FROM loans l JOIN loan_items i ON i.loan_id = l.id
                   WHERE l.borrower_id = ? AND l.status = 'active'
                     AND l.due_date < ? AND i.returned_at IS NULL LIMIT 1""",
                (borrower_id, bangkok_today().isoformat()),
            ).fetchone()
            if overdue:
                raise ValidationError("ผู้ใช้นี้มีรายการเกินกำหนด จึงยังยืมเพิ่มไม่ได้")
            marks = ",".join("?" for _ in unit_ids)
            available = db.execute(
                f"""SELECT id FROM equipment_units
                    WHERE id IN ({marks}) AND status = 'available'
                      AND equipment_type_id IN (SELECT id FROM equipment_types WHERE status = 'active')""",
                unit_ids,
            ).fetchall()
            if {row["id"] for row in available} != set(unit_ids):
                raise ValidationError("มีอุปกรณ์อย่างน้อยหนึ่งชิ้นที่ไม่พร้อมยืม")
            sequence = db.execute("SELECT COUNT(*) + 1 FROM loans WHERE borrow_date = ?", (borrow_date.isoformat(),)).fetchone()[0]
            code = f"LN-{borrow_date:%Y%m%d}-{sequence:03d}"
            loan_id = db.execute(
                "INSERT INTO loans(code, borrower_id, borrow_date, due_date, created_by_user_id) VALUES (?, ?, ?, ?, ?)",
                (code, borrower_id, borrow_date.isoformat(), due_date.isoformat(), actor_id),
            ).lastrowid
            db.executemany("INSERT INTO loan_items(loan_id, equipment_unit_id) VALUES (?, ?)", ((loan_id, unit_id) for unit_id in unit_ids))
            db.executemany(
                "UPDATE equipment_units SET status = 'borrowed', updated_at = ? WHERE id = ? AND status = 'available'",
                ((utc_text(), unit_id) for unit_id in unit_ids),
            )
            db.commit()
            return db.execute(
                """SELECT l.*, u.username, u.full_name, u.line_user_id,
                          (SELECT COUNT(*) FROM loan_items WHERE loan_id = l.id) AS item_count
                   FROM loans l JOIN users u ON u.id = l.borrower_id WHERE l.id = ?""",
                (loan_id,),
            ).fetchone()

    def return_items(self, actor_id: int, loan_id: int, item_ids: list[int], returned_at: datetime | None = None) -> sqlite3.Row:
        if not item_ids or len(item_ids) != len(set(item_ids)):
            raise ValidationError("กรุณาเลือกรายการคืนโดยไม่ซ้ำกัน")
        timestamp = utc_text(returned_at)
        with connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_admin(db, actor_id)
            loan = db.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()
            if loan is None or loan["status"] != "active":
                raise ValidationError("รายการยืมนี้ปิดแล้วหรือไม่มีอยู่")
            marks = ",".join("?" for _ in item_ids)
            rows = db.execute(
                f"SELECT * FROM loan_items WHERE id IN ({marks}) AND loan_id = ? AND returned_at IS NULL",
                (*item_ids, loan_id),
            ).fetchall()
            if {row["id"] for row in rows} != set(item_ids):
                raise ValidationError("มีอุปกรณ์ที่คืนแล้วหรือไม่ได้อยู่ในรายการนี้")
            db.executemany(
                "UPDATE loan_items SET returned_at = ?, received_by_user_id = ? WHERE id = ?",
                ((timestamp, actor_id, item_id) for item_id in item_ids),
            )
            db.executemany(
                "UPDATE equipment_units SET status = 'available', updated_at = ? WHERE id = ?",
                ((timestamp, row["equipment_unit_id"]) for row in rows),
            )
            outstanding = db.execute("SELECT COUNT(*) FROM loan_items WHERE loan_id = ? AND returned_at IS NULL", (loan_id,)).fetchone()[0]
            if outstanding == 0:
                db.execute("UPDATE loans SET status = 'completed', completed_at = ? WHERE id = ?", (timestamp, loan_id))
            db.commit()
            return db.execute(
                """SELECT l.*, u.username, u.full_name, u.line_user_id,
                          (SELECT COUNT(*) FROM loan_items WHERE loan_id = l.id) AS item_count,
                          (SELECT COUNT(*) FROM loan_items WHERE loan_id = l.id AND returned_at IS NULL) AS outstanding_count
                   FROM loans l JOIN users u ON u.id = l.borrower_id WHERE l.id = ?""",
                (loan_id,),
            ).fetchone()

    def list_loans(self, query: str = "", *, status: str | None = None, borrower_id: int | None = None) -> list[sqlite3.Row]:
        where = ["1 = 1"]
        values: list[object] = []
        if query.strip():
            term = f"%{query.strip()}%"
            where.append("(l.code LIKE ? OR u.username LIKE ? OR u.full_name LIKE ?)")
            values.extend((term, term, term))
        if status in {"active", "completed"}:
            where.append("l.status = ?")
            values.append(status)
        if borrower_id is not None:
            where.append("l.borrower_id = ?")
            values.append(borrower_id)
        with connect(self.path) as db:
            return db.execute(
                f"""SELECT l.*, u.username, u.full_name,
                       COUNT(i.id) AS item_count,
                       SUM(CASE WHEN i.returned_at IS NULL THEN 1 ELSE 0 END) AS outstanding_count
                    FROM loans l JOIN users u ON u.id = l.borrower_id
                    JOIN loan_items i ON i.loan_id = l.id
                    WHERE {' AND '.join(where)}
                    GROUP BY l.id ORDER BY l.created_at DESC""",
                values,
            ).fetchall()

    def loan_items(self, loan_id: int, *, outstanding_only: bool = False) -> list[sqlite3.Row]:
        extra = "AND i.returned_at IS NULL" if outstanding_only else ""
        with connect(self.path) as db:
            return db.execute(
                f"""SELECT i.*, eu.asset_code, eu.storage_location, et.name AS type_name
                    FROM loan_items i JOIN equipment_units eu ON eu.id = i.equipment_unit_id
                    JOIN equipment_types et ON et.id = eu.equipment_type_id
                    WHERE i.loan_id = ? {extra} ORDER BY eu.asset_code""",
                (loan_id,),
            ).fetchall()

    def user_history(self, user_id: int) -> list[sqlite3.Row]:
        return self.list_loans(borrower_id=user_id)

    def dashboard(self, user: User) -> dict[str, int]:
        today = bangkok_today().isoformat()
        with connect(self.path) as db:
            if user.role == "admin":
                return {
                    "active": db.execute("SELECT COUNT(*) FROM loans WHERE status = 'active'").fetchone()[0],
                    "overdue": db.execute("SELECT COUNT(*) FROM loans WHERE status = 'active' AND due_date < ?", (today,)).fetchone()[0],
                    "due_today": db.execute("SELECT COUNT(*) FROM loans WHERE status = 'active' AND due_date = ?", (today,)).fetchone()[0],
                    "returned_today": db.execute("SELECT COUNT(*) FROM loan_items WHERE date(returned_at, '+7 hours') = ?", (today,)).fetchone()[0],
                    "available": db.execute("SELECT COUNT(*) FROM equipment_units WHERE status = 'available'").fetchone()[0],
                }
            return {
                "active": db.execute("SELECT COUNT(*) FROM loans WHERE borrower_id = ? AND status = 'active'", (user.id,)).fetchone()[0],
                "overdue": db.execute("SELECT COUNT(*) FROM loans WHERE borrower_id = ? AND status = 'active' AND due_date < ?", (user.id, today)).fetchone()[0],
                "available": db.execute("SELECT COUNT(*) FROM equipment_units WHERE status = 'available'").fetchone()[0],
            }

    def claim_due_reminders(self, today: date | None = None) -> list[LineMessage]:
        current = (today or bangkok_today()).isoformat()
        messages: list[LineMessage] = []
        with connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            for days, column in ((3, "reminder_3d_at"), (1, "reminder_1d_at")):
                rows = db.execute(
                    f"""SELECT l.id, l.code, l.due_date, u.line_user_id
                        FROM loans l JOIN users u ON u.id = l.borrower_id
                        WHERE l.status = 'active' AND u.line_user_id IS NOT NULL
                          AND date(l.due_date, '-{days} day') = ? AND l.{column} IS NULL""",
                    (current,),
                ).fetchall()
                for row in rows:
                    db.execute(f"UPDATE loans SET {column} = ? WHERE id = ? AND {column} IS NULL", (utc_text(), row["id"]))
                    messages.append(LineMessage(row["line_user_id"], f"รายการ {row['code']} จะครบกำหนดในอีก {days} วัน ({row['due_date']})"))
            db.commit()
        return messages
