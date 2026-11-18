# Báo cáo kiểm thử Backend API qua CLI

## 1. Tóm tắt

- Ngày chạy: 2026-11-16 (Asia/Bangkok).
- Môi trường: Windows, PowerShell; Docker 29.9.2; Docker Compose v5.6.1; PostgreSQL 16.15; Mosquitto 2.0.22; Python server header 3.14.3; curl 8.21.0 (Windows/Schannel). Không tìm thấy lệnh postman hoặc newman; dùng curl.exe.
- Phương pháp: CLI/terminal và database test cô lập. Không dùng Swagger UI, Postman UI hoặc dashboard.
- Tổng 18 ca: 14 PASS, 1 FAIL, 1 BLOCKED, 2 N/A.
- Đánh giá: API GET cơ bản, lọc, validation query, DB error/recovery hoạt động theo expected trong test; chưa thể xác minh MQTT ingest do broker test không hoàn tất MQTT handshake từ host. Chưa đủ bằng chứng để kết luận toàn bộ backend E2E ổn.
- Expected outputs được ghi trước khi thực hiện các ca tương ứng tại bản kế hoạch ban đầu trong báo cáo. Một số URL khám phá bổ sung (/docs, /swagger, /redoc) được thử sau khi đã ghi expected cho /openapi.json; các kết quả đó chỉ là quan sát khám phá, không tính như ca PASS theo quy trình expected-first.

## 2. Khám phá

Nguồn: README.md; backend/README.md; web/README.md; backend/config.py; backend/domain/contract.py, validator.py, query.py; backend/interfaces/http_api.py; backend/infrastructure/migrations.py; backend/migrations/001_create_posture_events.sql; backend/repositories/event_repository.py; web/app_web.py; web/app.js; docker-compose.test.yml; tests/integration/test_mqtt_recovery.py.

- Endpoint trong router: GET /api/events/latest và GET /api/events; Content-Type JSON. Router trả 200 cho route thành công, 400 cho query ValueError/IndexError, 404 path lạ, 503 lỗi backend khác. Nguồn: backend/interfaces/http_api.py:33-63.
- History query cho phép from, to, seat_id, limit; default 100, tối đa 500. Không có offset/page; tham số không hỗ trợ bị reject. Nguồn: backend/README.md:31-34; backend/domain/query.py:10-46.
- MQTT topic mặc định classroom/posture/events; schema bắt buộc event_id, ts, seat_id, label, confidence, model, angles; nhãn upright/slouching/leaning/unknown; payload tối đa 16,384 byte. Nguồn: backend/config.py:12; backend/domain/contract.py:3-11.
- Validator source kiểm UUID, UTC, seat_id 1-32 ký tự, label enum, confidence hữu hạn trong [0,1] và không bool, góc hữu hạn/REAL; góc null chỉ hợp lệ với label unknown; từ chối field thừa. Nguồn: backend/domain/validator.py:13-85.
- DB posture_events có unique event_id, CHECK label/confidence, index ts và (seat_id,ts). Đã truy vấn catalog runtime, chi tiết ở DB-02. Nguồn migration: backend/migrations/001_create_posture_events.sql:1-12.
- Compose test khai báo postgres:16-alpine ở 127.0.0.1:15432 và eclipse-mosquitto:2.0 ở 127.0.0.1:11883, healthcheck mỗi service, không volume. Nguồn: docker-compose.test.yml:1-25.
- Chưa thấy router/OpenAPI cho /docs, /openapi.json, /swagger, /redoc; các route này được kiểm tra bằng curl ở API-03.
- History filtering đã triển khai. Server pagination/offset không có. Không tìm thấy has_skeleton, API skeleton, CSV export hoặc purge keypoints trong source đã rà soát; đánh N/A, không suy ra hành vi UI.
- README backend nêu lệnh test stack: docker compose -p posture-test -f docker-compose.test.yml up -d --wait; dùng đúng stack này. API local được khởi chạy với DB_HOST/PORT/NAME/USER trỏ test DB, PORT=18000; subscriber thử với MQTT_HOST=127.0.0.1, MQTT_PORT=11883.
- Không đọc/in nội dung .env. Backend nạp cấu hình nhưng mọi biến DB/MQTT liên quan được override bằng giá trị test trước khi process chạy; test password chỉ được lấy nội bộ từ container test vào biến tiến trình, không echo/ghi lại.

## 3. Kết quả

| ID | Mô tả / INPUT / cách làm | OUTPUT MONG ĐỢI (nguồn) | OUTPUT THỰC TẾ | Kết quả |
|---|---|---|---|---|
| ENV-01 | Kiểm tra Docker/curl/Python, Postman CLI và trạng thái project test trước khi chạy | Docker/Compose sẵn có; xác định trạng thái stack; README backend mục Tests | Docker 29.9.2, Compose 5.6.1, curl 8.21.0, Python 3.14; postman/newman không có output; project posture-test ban đầu rỗng khi truy vấn có quyền Docker | PASS |
| INFRA-01 | docker compose -p posture-test -f docker-compose.test.yml up -d --wait | Hai service test healthy theo compose healthcheck | Exit 0; posture-test-postgres-1 và posture-test-mqtt-broker-1 Started, sau đó Healthy | PASS |
| API-SRV-01 | Khởi động python -u -m backend.api với DB chỉ tới test DB, PORT=18000 | Migration thành công, server listen 127.0.0.1:18000 | Log: [api] listening on 127.0.0.1:18000; database=PostgreSQL. Lần thử đầu không có quyền gọi Docker để lấy test credential nên fail trước request; lần chạy được duyệt thành công | PASS |
| DB-01 | Query server_version, số dòng posture_events và schema_migrations trước seed | DB test rỗng, migration 001 đã áp | PostgreSQL 16.15; count=0; migration=001_create_posture_events.sql | PASS |
| DB-02 | Query pg_indexes và pg_constraint | Có PK, unique event_id, CHECK label/confidence, hai index theo migration | Runtime trả idx_posture_events_seat_ts, idx_posture_events_ts, posture_events_event_id_key UNIQUE, posture_events_pkey; constraints PK(id), UNIQUE(event_id), CHECK label enum, CHECK confidence [0,1] | PASS |
| API-01 | curl GET /api/events/latest khi DB trống | 200, JSON array rỗng theo router/repository | HTTP/1.0 200 OK; Content-Type application/json; charset=utf-8; body []; curl 0.047996 s | PASS |
| API-02 | curl GET /api/events khi DB trống | 200, JSON array rỗng; default limit 100 theo README/query parser | HTTP/1.0 200 OK; cùng Content-Type; body []; curl 0.028509 s | PASS |
| API-03 | GET /openapi.json; exploratory GET /docs, /swagger, /redoc | Với /openapi.json: 404 JSON vì không có route theo http_api.py:33-56 | Bốn URL đều trả 404 JSON {"error": "Not found"}. /openapi.json 0.010006 s. Ba URL bổ sung chỉ ghi nhận khám phá vì expected chưa được ghi trước | N/A — không có OpenAPI tại các đường dẫn đã dò; finding P3 |
| API-04 | POST /api/events | Không có POST route; HTTP server chuẩn từ chối method | HTTP/1.0 501 Unsupported method ('POST'); Content-Type text/html;charset=utf-8; HTML nêu Error code: 501 / Unsupported method ('POST'); 0.003369 s | PASS — hành vi method không hỗ trợ |
| API-05 | GET /missing-route | 404 JSON theo http_api.py:53-56 | HTTP/1.0 404 Not Found; body {"error": "Not found"}; application/json; charset=utf-8; 0.003431 s | PASS |
| API-06 | GET history với limit=abc, from=not-a-time, from > to | 400 JSON Invalid query parameters theo query.py và handler | Từng request trả HTTP 400, body {"error": "Invalid query parameters"}; các thời gian đo 0.002657 s, 0.005518 s, 0.002690 s. Có một URL thử đầu encode nhầm dấu & thành %26, cũng trả 400 do timestamp hỏng; không dùng URL đó làm bằng chứng from>to | PASS |
| API-07 | limit=501, -1, 1000000 | 400 do giới hạn 1..500 theo contract/query.py:43-45 | Cả ba trả HTTP 400 JSON {"error": "Invalid query parameters"}; lần lượt 0.003738 s, 0.002668 s, 0.002453 s | PASS |
| API-08 | SQL seed hai hàng test-only, sau đó GET latest/history, lọc seat/time, limit=1, offset=0 | API trả đúng 2 hàng theo source; history mới nhất trước; offset không hợp lệ vì parser không cho phép | SQL INSERT 0 2: TEST-A1 upright 0.93 tại 04:00Z (event …00a1), TEST-B2 slouching 0.82 tại 04:01Z (event …00b2). Latest trả cả hai. History trả TEST-B2 trước TEST-A1. seat TEST-A1 và bộ lọc UTC trả đúng một hàng. limit=1 trả TEST-B2. offset=0 trả 400 Invalid query parameters. GET thời gian 0.018–0.049 s | PASS — seed trực tiếp DB, không phải MQTT ingest |
| API-09 | GET /api/events?seat_id=TEST-NONE | 200 JSON [] | HTTP/1.0 200 OK; body []; 0.066732 s | PASS |
| API-10 | Tạm dừng PostgreSQL test, GET latest; khởi động DB, gọi lại | DB down: 503 JSON theo http_api.py:57-63; sau phục hồi: 200 | Khi DB dừng: HTTP/1.0 503 Service Unavailable, body {"error": "Service temporarily unavailable"}, 5.004341 s. Compose báo Healthy khi khởi động lại. GET sau đó 200 và hai hàng test vẫn đọc được, 0.041153 s | PASS |
| MQTT-00 | TCP check và Paho MQTT handshake từ host tới 127.0.0.1:11883 | Host client handshake được theo cách tests/integration/test_mqtt_recovery.py dùng TEST_MQTT_PORT | TCP TcpTestSucceeded=True. Paho: connect_return=0; on_disconnect=Unspecified error hai lần; is_connected=False. Broker log: Starting in local only mode. Không thấy posture-backend trong log | FAIL — test broker không hoàn tất handshake client host |
| MQTT-01 | Payload hợp lệ nhiều ghế, duplicate, payload lỗi, reconnect broker/DB, đối chiếu subscriber/DB/API | Subscriber ready; valid ghi một lần, duplicate bỏ qua, invalid bị từ chối theo validator/repository | Subscriber chỉ log disconnected: reason=Unspecified error; reconnect will be attempted; không có ready/subscribed. Không gửi payload MQTT để tránh báo sai kết quả | BLOCKED — broker test không nhận session từ host |
| FEATURE-01 | has_skeleton, API keypoints/skeleton, CSV export, purge keypoints | Chỉ test nếu feature có triển khai | Không tìm thấy endpoint/field/script tương ứng trong source đã rà; không chạy runtime | N/A — chưa thấy triển khai |

Lệnh, exit code, output và response đã quan sát được lưu ở commands.md. Thời gian curl là mẫu đo của từng request trong môi trường local, không phải cam kết hiệu năng.

## 4. Danh sách lỗi / phát hiện

### P2 — MQTT test broker chạy local-only, chặn kiểm thử subscriber từ host

- Tái hiện: khởi động compose test; chạy subscriber với MQTT_HOST=127.0.0.1 và MQTT_PORT=11883; quan sát callback disconnect; thử Paho client độc lập.
- Expected: host subscriber kết nối và subscribe theo tests/integration/test_mqtt_recovery.py; Compose publish port 11883.
- Actual: TCP mở nhưng MQTT client ngắt ngay; Mosquitto 2.0.22 log “Starting in local only mode. Connections will only be possible from clients running on this machine.” Compose command là mosquitto -p 1883 (docker-compose.test.yml:16-22), healthcheck chạy từ bên trong container.
- Ảnh hưởng: không thể kiểm thử MQTT→subscriber→DB bằng test harness hiện có. Chưa kết luận broker cấu hình sản phẩm hoặc backend production bị lỗi.
- Đề xuất: điều chỉnh cấu hình broker test để có listener cho network test và giới hạn phạm vi ở loopback/test network; sau đó chạy lại integration/recovery.

### P3 — Không có OpenAPI/Swagger ở các đường dẫn phổ biến

- Tái hiện qua curl: GET /openapi.json, /docs, /swagger, /redoc.
- Actual: 404 JSON {"error": "Not found"} cho cả bốn.
- Nguồn nghi ngờ: backend/interfaces/http_api.py:33-56 chỉ đăng ký /api/events/latest và /api/events.
- Đề xuất: cân nhắc công bố OpenAPI nếu nhóm cần công cụ khám phá/collection API.

Không ghi finding về confidence bool/NaN runtime: source có kiểm tra, nhưng MQTT ingest runtime bị chặn.

## 5. Chưa xác minh

- MQTT payload valid/invalid, duplicate, subscriber reconnect và DB/MQTT recovery chưa chạy được vì handshake không thành công.
- confidence bool và góc NaN/Infinity: chỉ thấy source validator; không xác minh runtime.
- Các truy vấn DB test và API response đã kiểm tra; không kiểm tra production DB/broker.
- Swagger UI, Postman UI, dashboard rendering, DevTools Console/Network, responsive layout, tải/mở CSV qua trình duyệt và screenshot không thuộc phương pháp CLI, chưa kiểm tra.
- Không có camera/vision inference hoặc lớp học thật; không đo model accuracy, camera latency hay end-to-end camera-to-dashboard latency.
- Mọi dữ liệu API là tổng hợp; giả định mỗi ghế một người, chưa kiểm chứng với nhiều người thực.

## 6. Dọn dẹp

- Xóa chỉ hai event ID do lượt này seed, không dùng pattern rộng. DELETE trả hai event IDs với seat TEST-A1/TEST-B2 và DELETE 2; truy vấn xác minh còn 0 dòng khớp hai ID.
- Dừng API process do lượt này khởi động bằng Ctrl+C.
- Chạy docker compose -p posture-test -f docker-compose.test.yml down; hai container và network posture-test được dừng/xóa. Không dùng -v; compose không khai báo volume.
- Không còn dữ liệu test do lượt này tạo trong DB test.

## 7. Xác nhận

Không sửa mã nguồn, không tạo nhánh, không commit/push. Không đọc/in .env, không ghi credential/secret vào báo cáo. Không tạo screenshot giả. Lượt này chỉ chạy các request/API trên stack test và ghi rõ các ca chưa kiểm tra.
