"""Nhận một bản tin thô: kiểm tra, lưu, thử lại có giới hạn và phân loại kết quả.

Tầng giao tiếp (MQTT) dựa vào `Outcome` để quyết định ACK hay ngắt kết nối.
"""

from dataclasses import dataclass
from enum import Enum, auto
import time
from typing import Callable

from backend.domain.errors import StorageRejectedError, StorageUnavailableError
from backend.domain.validator import decode_event_message
from backend.repositories import event_repository


class Outcome(Enum):
    STORED = auto()
    DUPLICATE = auto()
    INVALID = auto()
    TEMPORARY = auto()
    PERMANENT = auto()


@dataclass(frozen=True)
class ProcessResult:
    outcome: Outcome
    reason: str | None = None
    error_type: str | None = None


RETRY_DELAYS = (0.5, 1.0)
MAX_ATTEMPTS = len(RETRY_DELAYS) + 1


def handle_payload(
    raw: bytes,
    insert: Callable[[dict], bool] | None = None,
) -> ProcessResult:
    """Validate and store one payload once, classifying retryable errors."""
    insert = insert or event_repository.insert_event
    valid, reason, event = decode_event_message(raw)
    if not valid:
        return ProcessResult(Outcome.INVALID, reason=reason)
    try:
        if insert(event):
            return ProcessResult(Outcome.STORED)
        return ProcessResult(Outcome.DUPLICATE)
    except StorageRejectedError as exc:
        return ProcessResult(Outcome.PERMANENT, error_type=exc.cause_type)
    except StorageUnavailableError as exc:
        return ProcessResult(Outcome.TEMPORARY, error_type=exc.cause_type)
    except Exception as exc:
        # Unexpected storage errors fail closed and use the same bounded retry.
        return ProcessResult(Outcome.TEMPORARY, error_type=type(exc).__name__)


def ingest(
    raw: bytes,
    insert: Callable[[dict], bool] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> ProcessResult:
    """Handle a payload, retrying temporary storage failures with bounded backoff."""
    result = ProcessResult(Outcome.TEMPORARY, error_type="UnknownError")
    for attempt in range(MAX_ATTEMPTS):
        result = handle_payload(raw, insert)
        if result.outcome is not Outcome.TEMPORARY:
            break
        if attempt < len(RETRY_DELAYS):
            sleep(RETRY_DELAYS[attempt])
    return result
