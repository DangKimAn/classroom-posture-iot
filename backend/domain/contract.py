"""Hằng số của hợp đồng dữ liệu (docs/agent/DATA_CONTRACT.md). Đổi ở đây = đổi hợp đồng: dùng skill change-contract."""

LABELS = frozenset({"upright", "slouching", "leaning", "unknown"})
REQUIRED_FIELDS = frozenset({"event_id", "ts", "seat_id", "label", "confidence", "model", "angles"})

MAX_PAYLOAD_BYTES = 16_384
MAX_POSTGRES_REAL = 3.4028234663852886e38

# Giới hạn REST API.
DEFAULT_LIMIT = 100
MAX_LIMIT = 500
MAX_SEAT_ID_LENGTH = 32
