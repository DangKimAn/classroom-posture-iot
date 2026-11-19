# Kiến trúc phân tầng của backend (TV3)

Mục tiêu: mỗi file có một việc, biết rõ nên sửa ở đâu khi thêm tính năng, và kiểm tra từng tầng độc lập (không cần broker hay PostgreSQL). Cấu trúc này **không đổi hợp đồng**: topic, JSON event, bảng `posture_events` và đường dẫn API giữ nguyên.

## Sơ đồ

```
 MQTT broker                                   Trình duyệt / Nginx
     │                                                │
     ▼                                                ▼
┌──────────────────────── interfaces/ ──────────────────────────┐   Tầng 5: giao tiếp vào/ra
│  mqtt_consumer.py (ACK/ngắt kết nối)   http_api.py (route, JSON, mã lỗi) │
└───────────────┬───────────────────────────────┬───────────────┘
                ▼                               ▼
┌──────────────────────── services/ ────────────────────────────┐   Tầng 4: nghiệp vụ
│  ingest_service.py (kiểm tra, retry, phân loại)                │
│  event_query_service.py (truy vấn cho dashboard)               │
└───────────────────────────────┬───────────────────────────────┘
                                ▼
┌──────────────────────── repositories/ ────────────────────────┐   Tầng 3: SQL
│  event_repository.py (insert / latest / query, dịch lỗi DB)    │
└───────────────────────────────┬───────────────────────────────┘
                                ▼
┌──────────────────────── infrastructure/ ──────────────────────┐   Tầng 2: kết nối ngoài
│  database.py (connect)    migrations.py (áp dụng migrations/*.sql) │
└───────────────────────────────────────────────────────────────┘

 domain/   Tầng 1 (thuần, không I/O): contract.py, validator.py, query.py, errors.py, timeutil.py
 config.py Tầng 0: biến môi trường -> settings
api.py, mqtt_subscriber.py: điểm vào (composition root), chỉ nối các tầng với nhau
retention.py: entry point mỏng cho lệnh retention; logic CLI thuộc interfaces/retention_cli.py
```

## Trách nhiệm từng tầng

| Tầng | Làm | Không được làm | Được import |
| --- | --- | --- | --- |
| `config.py` | Đọc `.env`/biến môi trường thành settings | Biết SQL, MQTT, HTTP | không có |
| `domain/` | Hằng số hợp đồng, kiểm tra payload và tham số, lỗi nghiệp vụ | I/O, import psycopg/paho/http | chỉ `domain` |
| `infrastructure/` | Mở kết nối PostgreSQL, áp dụng migration | Câu lệnh nghiệp vụ | `config` |
| `repositories/` | Mọi câu SQL; dịch lỗi psycopg thành `StorageRejectedError`/`StorageUnavailableError` | Quy tắc nghiệp vụ, HTTP | `infrastructure`, `domain` |
| `services/` | Quy tắc nghiệp vụ: kiểm tra → lưu → retry → phân loại kết quả; logic thống kê sau này | Biết HTTP/MQTT/psycopg | `repositories`, `domain`, `config` |
| `interfaces/` | Chuyển đổi giao thức: nhận dữ liệu, gọi service, trả JSON/ACK | SQL, tự quyết nghiệp vụ | `services`, `domain`, `config` |
| `api.py`, `mqtt_subscriber.py` | Nạp `.env`, chạy migration, khởi động interface | Chứa logic (tối đa 40 dòng) | mọi tầng |
| `retention.py` | Chuyển tiếp lệnh `python -m backend.retention` tới CLI ở `interfaces/` | Chứa xử lý tham số, truy vấn DB hoặc logic retention | `interfaces` |

Phụ thuộc chỉ đi **từ trên xuống**; tầng dưới không được import ngược tầng trên.

## Hai luồng chạy

**Nhận event (MQTT):** `mqtt_consumer.process_message` → `ingest_service.ingest` (thử tối đa 3 lần theo `RETRY_DELAYS`) → `ingest_service.handle_payload` → `domain.validator.decode_event_message` → `event_repository.insert_event`. Kết quả là `Outcome`; interface ACK khi `STORED`, `DUPLICATE`, `INVALID`, `PERMANENT` và ngắt kết nối khi `TEMPORARY` để broker giao lại.

**Truy vấn (HTTP):** `ApiHandler.do_GET` → `ROUTES[path]` → `domain.query.parse_event_query` (ném `ValueError` → 400) → `event_query_service` → `event_repository`. Lỗi khác → 503.

## Thêm tính năng ở đâu

Ví dụ thêm `GET /api/stats/timeline` (chỉ làm sau khi PR hợp đồng được duyệt, xem `docs/contract_change_timeline_status_latency.md`):

1. `domain/query.py`: thêm `TimelineQuery` và hàm kiểm tra tham số (giới hạn khoảng thời gian, số bucket).
2. `repositories/event_repository.py`: thêm hàm `timeline_counts(...)` chứa câu SQL gom theo phút.
3. `services/event_query_service.py` (hoặc file service mới): tính tỷ lệ, loại ghế vắng.
4. `interfaces/http_api.py`: viết `route_timeline(params)` rồi đăng ký vào `ROUTES`.

Thêm cột như `received_at`: thêm `backend/migrations/002_*.sql` (idempotent), sửa `event_repository`, và `domain/contract.py` nếu hợp đồng đổi. Thêm quy tắc kiểm tra payload: sửa `domain/validator.py`. Thêm biến môi trường: chỉ khai báo trong `config.py`.

## Ánh xạ từ cấu trúc cũ

| Cũ | Mới |
| --- | --- |
| `validator.py` | `domain/validator.py` (hằng số sang `domain/contract.py`) |
| `database.connect` | `infrastructure/database.py` |
| `database.initialize` | `infrastructure/migrations.py` |
| `database.insert_event`, `latest_events`, `query_events` | `repositories/event_repository.py` |
| `mqtt_subscriber.handle_payload`, `Outcome`, `ProcessResult` | `services/ingest_service.py` |
| `mqtt_subscriber.process_message`, `main` | `interfaces/mqtt_consumer.py` (`process_message`, `run`) |
| `api.py` (handler, `_utc_param`) | `interfaces/http_api.py`, `domain/query.py` |
| `config.py` | `config.py` (thêm settings có kiểu) |

## Chạy ứng dụng

Chạy từ **thư mục gốc repo** (không còn chạy trực tiếp `python backend/api.py`):

```
python -m backend.api
python -m backend.mqtt_subscriber
```

Docker: `backend/Dockerfile` dùng `PYTHONPATH=/app` và `python -m backend.api`; service `subscriber` trong `docker-compose.yml` dùng `python -m backend.mqtt_subscriber`.
