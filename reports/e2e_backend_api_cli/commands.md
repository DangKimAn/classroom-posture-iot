# Nhật ký lệnh kiểm thử

Không đọc/in `.env`. File đã được cập nhật bằng output thực tế sau khi hoàn tất kiểm thử.

## Preflight

Expected trước khi chạy: kiểm tra sự hiện diện/phiên bản công cụ và trạng thái hiện có của compose project `posture-test`; không thay đổi dịch vụ.

- Lệnh: `Get-Command docker,curl.exe,python -ErrorAction SilentlyContinue | Select-Object Name,Source,Version`
- Lệnh: `docker --version`
- Lệnh: `docker compose version`
- Lệnh: `docker compose -p posture-test -f docker-compose.test.yml ps`
- Lần đầu exit 1 do sandbox từ chối Docker API; sau đó chạy lại với quyền Docker được duyệt: exit 0, chỉ có header NAME IMAGE COMMAND SERVICE CREATED STATUS PORTS, không có service. Project test ban đầu rỗng.

## Test runtime

Thực thi đã hoàn tất. Trước mỗi nhóm test, expected output đã ghi tại `report.md`; các lệnh chính xác, output quan sát được và exit code được lưu trong nhật ký bên dưới.

## Cleanup

Đã xóa hai event ID riêng của lượt chạy và dừng đúng stack/service do lượt này khởi động; chi tiết cuối file.

## Preflight thực tế

### Lệnh 1 — công cụ

- Lệnh: `Get-Command docker,curl.exe,python -ErrorAction SilentlyContinue | Select-Object Name,Source,Version`
- Exit code: `0`
- Output:
```text
Name       Source                                                                       Version
----       ------                                                                       -------
docker.exe C:\Users\Admin\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe 0.0.0.0
curl.exe   C:\WINDOWS\system32\curl.exe                                                 8.21.0.0
python.exe C:\Users\Admin\AppData\Local\Programs\Python\Python314\python.exe            3.14.3150.1013
```

### Lệnh 2 — Docker

- Lệnh: `docker --version`
- Exit code: `0`
- Output: `Docker version 29.9.2, build a82e528`

### Lệnh 3 — Compose

- Lệnh: `docker compose version`
- Exit code: `0`
- Output: `Docker Compose version v5.6.1`

### Lệnh 4 — trạng thái stack thử nghiệm

- Lệnh: `docker compose -p posture-test -f docker-compose.test.yml ps`
- Exit code: `1`
- Output: `permission denied while trying to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`
- Kết luận: sandbox không truy cập được Docker daemon; chưa xác định được trạng thái project và chưa khởi động/dừng service.

## INFRA-01 — stack test riêng

Expected trước chạy: `docker compose -p posture-test -f docker-compose.test.yml up -d --wait` tạo PostgreSQL/Mosquitto test và đợi healthcheck.

- Lệnh: `docker compose -p posture-test -f docker-compose.test.yml up -d --wait`
- Exit code: `0`
- Output quan sát:
```text
Network posture-test_default Created
Container posture-test-postgres-1 Created
Container posture-test-mqtt-broker-1 Created
Container posture-test-postgres-1 Started
Container posture-test-mqtt-broker-1 Started
Container posture-test-postgres-1 Healthy
Container posture-test-mqtt-broker-1 Healthy
```
- Actual: hai service test healthy; image khai báo trong compose là postgres:16-alpine và eclipse-mosquitto:2.0. Đây là tag cấu hình, chưa phải phiên bản runtime đã truy vấn.

## API process startup attempt 1 (failed)

Expected trước chạy: API migration kết nối PostgreSQL test; sau đó in `[api] listening on 127.0.0.1:18000; database=PostgreSQL`.

- Lệnh (giá trị DB password không được ghi): đặt `DB_URL=''`, `DB_HOST=127.0.0.1`, `DB_PORT=15432`, `DB_NAME=posture_test`, `DB_USER=posture_test`; lấy password test từ `docker compose ... exec -T postgres printenv POSTGRES_PASSWORD` rồi chạy `python -u -m backend.api` với `PORT=18000`.
- Exit code: `1`.
- Output quan sát: Docker API bị `permission denied`; PowerShell biến nhận password rỗng; API traceback có `psycopg.OperationalError` / `password authentication failed for user "posture_test"`.
- Không có secret/password được in. Không gửi request API. Đây là lỗi khởi động do command subprocess không có quyền Docker, chưa phải lỗi ứng dụng.

## API process startup attempt 2 (successful)

Expected trước chạy: nạp cấu hình chỉ trỏ tới PostgreSQL test, áp migration, rồi lắng nghe 127.0.0.1:18000.

- Lệnh: PowerShell đặt DB_URL trống, host 127.0.0.1, port 15432, database/user posture_test; lấy mật khẩu chỉ từ container test vào biến tiến trình (không echo); PORT=18000; chạy python -u -m backend.api.
- Exit: process còn chạy (session 18221).
- Output thực tế: [api] listening on 127.0.0.1:18000; database=PostgreSQL.
- Kết quả: API khởi động và migration không báo lỗi.

## API baseline CLI results (expected đã ghi ở report trước khi request)

Mẫu lệnh: curl.exe -sS -i -w "`nCURL_HTTP_CODE=%{http_code}; CONTENT_TYPE=%{content_type}; TIME_TOTAL=%{time_total}`n" URL; riêng API-04 thêm -X POST. Tất cả exit code `0`.

- API-01 GET /api/events/latest — `HTTP/1.0 200 OK`; `Content-Type: application/json; charset=utf-8`; body `[]`; `CURL_HTTP_CODE=200`; `TIME_TOTAL=0.047996`.
- API-02 GET /api/events — `HTTP/1.0 200 OK`; `Content-Type: application/json; charset=utf-8`; body `[]`; `CURL_HTTP_CODE=200`; `TIME_TOTAL=0.028509`.
- API-03 GET /openapi.json — `HTTP/1.0 404 Not Found`; JSON body `{"error": "Not found"}`; `CURL_HTTP_CODE=404`; `TIME_TOTAL=0.010006`.
- API-04 POST /api/events — `HTTP/1.0 501 Unsupported method ('POST')`; `Content-Type: text/html;charset=utf-8`; standard-library HTML body states `Error code: 501`, `Unsupported method ('POST')`; `CURL_HTTP_CODE=501`; `TIME_TOTAL=0.003369`.
- API-05 GET /missing-route — `HTTP/1.0 404 Not Found`; JSON body `{"error": "Not found"}`; `CURL_HTTP_CODE=404`; `TIME_TOTAL=0.003431`.
- API-06 GET /api/events?limit=abc — `HTTP/1.0 400 Bad Request`; JSON body `{"error": "Invalid query parameters"}`; `CURL_HTTP_CODE=400`; `TIME_TOTAL=0.002657`.
- API-07 GET /api/events?limit=501 — `HTTP/1.0 400 Bad Request`; JSON body `{"error": "Invalid query parameters"}`; `CURL_HTTP_CODE=400`; `TIME_TOTAL=0.003738`.

Header `Server` reported `BaseHTTP/0.6 Python/3.14.3`; response dates 2026-11-16 05:47:10-11 GMT. Full headers were observed directly in tool output; above records the pertinent header/body/status/timing.

## MQTT broker reachability (expected trước)

- Lệnh: `Test-NetConnection -ComputerName 127.0.0.1 -Port 11883 -InformationLevel Detailed`
- Exit 0; `TcpTestSucceeded: True`.
- Lệnh Paho probe: Python here-string tạo client `cli-probe`, gọi `connect('127.0.0.1', 11883)`, loop 2 giây, in callback/connected state; không publish payload.
- Exit 0; actual: `connect_return=0`, `on_disconnect=Unspecified error` hai lần, `is_connected=False`.
- Subscriber startup session 44196 actual: `[mqtt] disconnected: reason=Unspecified error; reconnect will be attempted` lặp; không quan sát thấy `ready; subscribed topic=...`; dừng session do lượt này khởi chạy bằng Ctrl+C.
- Lệnh broker logs: `docker compose -p posture-test -f docker-compose.test.yml logs --no-color mqtt-broker`; actual log ghi Mosquitto `2.0.22`, `Starting in local only mode. Connections will only be possible from clients running on this machine.`
- Lệnh lọc: `docker compose -p posture-test -f docker-compose.test.yml logs --no-color mqtt-broker | Select-String -Pattern 'posture-backend|local only' | Select-Object -Last 10`; không thấy client id posture-backend.

## DB read-only verification

- `docker compose -p posture-test -f docker-compose.test.yml exec -T postgres psql -U posture_test -d posture_test -Atc "SHOW server_version;"` → exit 0, output `16.15`.
- `docker compose -p posture-test -f docker-compose.test.yml exec -T postgres psql -U posture_test -d posture_test -Atc "SELECT count(*) FROM posture_events; SELECT filename FROM schema_migrations ORDER BY filename;"` → exit 0, outputs `0` then `001_create_posture_events.sql`.

## API test seed and query

- Expected trước seed: two rows only in new test DB, with event IDs `00000000-0000-4000-8000-0000000000a1` / `00000000-0000-4000-8000-0000000000b2`, seats TEST-A1/TEST-B2.
- Lệnh INSERT chạy qua `docker compose ... exec -T postgres psql ...`; exit 0; `RETURNING` showed rows: `(…a1, TEST-A1, upright, 0.93)` and `(…b2, TEST-B2, slouching, 0.82)`; `INSERT 0 2`.
- Note: SQL seed trực tiếp, không giả là MQTT ingest.
- API-08a `GET /api/events/latest` → 200 JSON array có cả hai event TEST-A1/TEST-B2; 0.049103 s.
- API-08b `GET /api/events` → 200 JSON array newest-first: event …b2 TEST-B2 slouching rồi …a1 TEST-A1 upright; 0.025015 s.
- API-08c `GET /api/events?seat_id=TEST-A1` → 200, chỉ …a1; 0.018362 s.
- API-08d `GET /api/events?seat_id=TEST-A1&from=2026-11-16T03%3A59%3A00Z&to=2026-11-16T04%3A01%3A00Z` → 200, chỉ …a1; 0.042753 s.
- API-08e `GET /api/events?limit=1` → 200, chỉ newest …b2; 0.027351 s.
- API-09 `GET /api/events?seat_id=TEST-NONE` → 200 body `[]`; 0.066732 s.
- API-08f `GET /api/events?offset=0` → 400 body `{"error": "Invalid query parameters"}`; 0.002422 s; offset không được chấp nhận.
- API-06d `GET /api/events?from=2026-11-16T04%3A00%3A00Z&to=2026-11-16T03%3A00%3A00Z` → 400 body `{"error": "Invalid query parameters"}`; 0.002690 s.
- API-10 stop PostgreSQL test: `docker compose -p posture-test -f docker-compose.test.yml stop postgres` → exit 0, container stopped. GET latest → 503 JSON `{"error": "Service temporarily unavailable"}`; 5.004341 s. Restart `docker compose -p posture-test -f docker-compose.test.yml up -d --wait postgres` → exit 0, `Healthy`. GET latest recovered to 200 with both retained TEST events; 0.041153 s.

## OpenAPI routes and remaining invalid query variants

All use the same curl.exe -sS -i -w status/content-type/time pattern, exit code 0:
- GET /docs → 404 JSON `{"error": "Not found"}`, 0.003703 s.
- GET /swagger → 404 JSON `{"error": "Not found"}`, 0.002063 s.
- GET /redoc → 404 JSON `{"error": "Not found"}`, 0.002971 s.
- GET /api/events?from=not-a-time → 400 JSON `{"error": "Invalid query parameters"}`, 0.005518 s.
- GET /api/events?from=2026-11-16T04%3A00%3A00Z&to=2026-11-16T03%3A00%3A00Z (actual PowerShell single-quoted URL; ampersand separates query args) → 400 JSON `{"error": "Invalid query parameters"}`, 0.002690 s.
- GET /api/events?limit=-1 → 400 JSON `{"error": "Invalid query parameters"}`, 0.002668 s.
- GET /api/events?limit=1000000 → 400 JSON `{"error": "Invalid query parameters"}`, 0.002453 s.
- All above responses were `application/json; charset=utf-8`.

## Migration catalog, tool versions, and schema

- `docker compose -p posture-test -f docker-compose.test.yml exec -T postgres psql -U posture_test -d posture_test -c "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'posture_events' ORDER BY indexname;"` → exit 0; indexes: idx_posture_events_seat_ts, idx_posture_events_ts, posture_events_event_id_key UNIQUE, posture_events_pkey.
- `docker compose -p posture-test -f docker-compose.test.yml exec -T postgres psql -U posture_test -d posture_test -c "SELECT conname, contype, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'posture_events'::regclass ORDER BY conname;"` → exit 0; PK(id), UNIQUE(event_id), CHECK label enum, CHECK confidence 0..1.
- `curl.exe --version` → curl 8.21.0, Windows, libcurl/8.21.0, Schannel.
- `Get-Command postman,newman -ErrorAction SilentlyContinue | Select-Object Name,Source` → no output (neither CLI command found); requests therefore used curl.exe.

## Exact API requests

All commands use `curl.exe -sS -i -w "`nCURL_HTTP_CODE=%{http_code}; CONTENT_TYPE=%{content_type}; TIME_TOTAL=%{time_total}`n"` followed by the exact URL below; all completed with curl exit 0:
- `http://127.0.0.1:18000/api/events/latest`
- `http://127.0.0.1:18000/api/events`
- `http://127.0.0.1:18000/openapi.json`
- `http://127.0.0.1:18000/docs`
- `http://127.0.0.1:18000/swagger`
- `http://127.0.0.1:18000/redoc`
- `-X POST http://127.0.0.1:18000/api/events`
- `http://127.0.0.1:18000/missing-route`
- `http://127.0.0.1:18000/api/events?limit=abc`
- `http://127.0.0.1:18000/api/events?limit=501`
- `http://127.0.0.1:18000/api/events?from=not-a-time`
- PowerShell single-quoted URL: `http://127.0.0.1:18000/api/events?from=2026-11-16T04%3A00%3A00Z&to=2026-11-16T03%3A00%3A00Z`
- `http://127.0.0.1:18000/api/events?limit=-1`
- `http://127.0.0.1:18000/api/events?limit=1000000`
- `http://127.0.0.1:18000/api/events?seat_id=TEST-A1`
- PowerShell double-quoted URL: `http://127.0.0.1:18000/api/events?seat_id=TEST-A1&from=2026-11-16T03%3A59%3A00Z&to=2026-11-16T04%3A01%3A00Z`
- `http://127.0.0.1:18000/api/events?limit=1`
- `http://127.0.0.1:18000/api/events?seat_id=TEST-NONE`
- `http://127.0.0.1:18000/api/events?offset=0`

A first attempt to encode `&` as `%26` in API-06c resulted in one malformed `from` value and 400; that attempt does not prove from>to. The separately executed PowerShell single-quoted URL above correctly separated both parameters and also returned 400.

## Exact DB seed

`docker compose -p posture-test -f docker-compose.test.yml exec -T postgres psql -U posture_test -d posture_test -c "INSERT INTO posture_events (event_id, ts, seat_id, label, trunk_angle, confidence, model_version) VALUES ('00000000-0000-4000-8000-0000000000a1', '2026-11-16T04:00:00Z', 'TEST-A1', 'upright', 8.0, 0.93, 'cli-test'), ('00000000-0000-4000-8000-0000000000b2', '2026-11-16T04:01:00Z', 'TEST-B2', 'slouching', 24.5, 0.82, 'cli-test') RETURNING event_id, seat_id, label, confidence;"`
- Exit 0; exact rows returned and `INSERT 0 2`.

## API database failure/recovery commands

- `docker compose -p posture-test -f docker-compose.test.yml stop postgres` → exit 0; `Container posture-test-postgres-1 Stopped`.
- GET latest exact URL above while down → 503 JSON; 5.004341 s.
- `docker compose -p posture-test -f docker-compose.test.yml up -d --wait postgres` → exit 0; service `Healthy`.
- GET latest exact URL above after recovery → 200; both seed rows still returned; 0.041153 s.

## Cleanup thực tế

Expected trước cleanup: đúng hai IDs do lượt này seed bị xóa, count xác minh bằng 0.
- Lệnh delete: `docker compose -p posture-test -f docker-compose.test.yml exec -T postgres psql -U posture_test -d posture_test -c "DELETE FROM posture_events WHERE event_id IN ('00000000-0000-4000-8000-0000000000a1', '00000000-0000-4000-8000-0000000000b2') RETURNING event_id, seat_id;"`
- Actual: trả hai event IDs trên với TEST-A1/TEST-B2, `(2 rows)`, `DELETE 2`.
- Lệnh verify: `docker compose -p posture-test -f docker-compose.test.yml exec -T postgres psql -U posture_test -d posture_test -Atc "SELECT count(*) FROM posture_events WHERE event_id IN ('00000000-0000-4000-8000-0000000000a1', '00000000-0000-4000-8000-0000000000b2');"`
- Actual: `0`.
- Lệnh dừng API: Ctrl+C tới session 18221; session kết thúc, không còn process API từ lượt này.
- Lệnh dừng stack: `docker compose -p posture-test -f docker-compose.test.yml down`; exit 0; hai container và network posture-test Stopped/Removed. Không dùng `-v`.

## Trạng thái cuối

- API-SRV-01: process đã dừng.
- posture-test: đã down; chỉ do lượt này tạo sau khi preflight báo project rỗng.
- Event test đã xóa và xác minh không còn.
- Không có file .env/credential trong nhật ký này.


## Xác minh cleanup cuối

- docker compose -p posture-test -f docker-compose.test.yml ps → exit 0; chỉ header NAME IMAGE COMMAND SERVICE CREATED STATUS PORTS, không có container.
- Test-NetConnection -ComputerName 127.0.0.1 -Port 18000 -InformationLevel Quiet → exit 0, output WARNING: TCP connect to (127.0.0.1 : 18000) failed rồi False; API listener đã dừng.



## Exact process launch configuration (no credential value recorded)

API launch was run with Docker access approved. PowerShell assignments:
    $testPass = (& docker compose -p posture-test -f docker-compose.test.yml exec -T postgres printenv POSTGRES_PASSWORD).Trim()
    $env:DB_URL = ''
    $env:DB_HOST = '127.0.0.1'
    $env:DB_PORT = '15432'
    $env:DB_NAME = 'posture_test'
    $env:DB_USER = 'posture_test'
    $env:DB_PASSWORD = $testPass
    $env:PORT = '18000'
    python -u -m backend.api
The password was captured in a process variable and never printed or written to this log.

Subscriber launch attempt used the same DB assignments and password retrieval, plus:
    $env:MQTT_HOST = '127.0.0.1'
    $env:MQTT_PORT = '11883'
    $env:MQTT_USERNAME = ''
    $env:MQTT_PASSWORD = ''
    $env:MQTT_TOPIC = 'classroom/posture/events'
    python -u -m backend.mqtt_subscriber
It only emitted repeated disconnect callbacks and was stopped with Ctrl+C.

## Exact MQTT handshake probe

Python source piped to python -:
    import time
    import paho.mqtt.client as mqtt
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="cli-probe")
    client.on_connect = lambda _c, _u, _f, reason, _p=None: print(f"on_connect={reason}")
    client.on_disconnect = lambda _c, _u, _f, reason, _p=None: print(f"on_disconnect={reason}")
    print(f"connect_return={client.connect('127.0.0.1', 11883, keepalive=5)}")
    client.loop_start()
    time.sleep(2)
    print(f"is_connected={client.is_connected()}")
    client.disconnect()
    client.loop_stop()
Actual output: connect_return=0; on_disconnect=Unspecified error twice; is_connected=False; exit 0. No publish was sent.

## Exact test-only seed command

    docker compose -p posture-test -f docker-compose.test.yml exec -T postgres psql -U posture_test -d posture_test -c "INSERT INTO posture_events (event_id, ts, seat_id, label, trunk_angle, confidence, model_version) VALUES ('00000000-0000-4000-8000-0000000000a1', '2026-11-16T04:00:00Z', 'TEST-A1', 'upright', 8.0, 0.93, 'cli-test'), ('00000000-0000-4000-8000-0000000000b2', '2026-11-16T04:01:00Z', 'TEST-B2', 'slouching', 24.5, 0.82, 'cli-test') RETURNING event_id, seat_id, label, confidence;"
Actual exit 0, two rows returned, INSERT 0 2.

- Initial project-state check retry with Docker access approved: `docker compose -p posture-test -f docker-compose.test.yml ps`; exit 0; output header `NAME IMAGE COMMAND SERVICE CREATED STATUS PORTS` only, no rows. Confirmed project empty before this run created it.
- `Get-Command postman,newman -ErrorAction SilentlyContinue | Select-Object Name,Source` returned no rows; there is no Postman CLI/Newman command available in PATH.
