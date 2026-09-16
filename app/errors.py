class AppError(Exception):
    """ข้อความผิดพลาดที่แสดงต่อผู้ใช้ได้โดยตรง"""


class ValidationError(AppError):
    pass


class AuthenticationError(AppError):
    pass


class PermissionDenied(AppError):
    pass


class NotFoundError(AppError):
    pass
