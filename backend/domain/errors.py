"""Lỗi nghiệp vụ độc lập với công nghệ lưu trữ.

Repository dịch lỗi PostgreSQL thành hai lỗi này, để service không cần biết psycopg.
"""


class StorageError(Exception):
    """Base class; `cause_type` keeps the original exception class name for safe logging."""

    def __init__(self, cause_type: str) -> None:
        super().__init__(cause_type)
        self.cause_type = cause_type


class StorageUnavailableError(StorageError):
    """Tạm thời không lưu được (mất kết nối, timeout...). Có thể thử lại."""


class StorageRejectedError(StorageError):
    """Dữ liệu bị cơ sở dữ liệu từ chối vĩnh viễn (sai kiểu/ràng buộc). Thử lại cũng vô ích."""
