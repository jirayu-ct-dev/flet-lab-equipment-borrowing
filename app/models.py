from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class User:
    id: int
    username: str
    full_name: str
    role: str
    user_type: str
    status: str
    must_change_password: bool
    backup_email: str | None = None
    faculty_id: int | None = None
    department_id: int | None = None
    cohort_id: int | None = None
    class_group_id: int | None = None
    line_user_id: str | None = None


@dataclass(frozen=True, slots=True)
class LineMessage:
    line_user_id: str
    text: str
