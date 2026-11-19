# Lệnh và output kiểm thử

Credential không được ghi ở đây. Auth fixture sinh credential trong process, truyền qua environment/stdin và che output trước khi ghi. Không đọc `.env` hay password file thật. Test data dùng `posture-test` riêng.

## Khả năng phiên

- Terminal PowerShell: hoạt động.
- Screenshot/browser input/DevTools: không có tool trong phiên; do đó không có ảnh chụp giao diện.

## Docker và A

| Lệnh | Output thực tế |
|---|---|
| `docker info --format '{{.ServerVersion}}'` | `29.9.2` (lệnh read-only qua quyền Docker được duyệt). |
| `docker compose -p posture-test -f docker-compose.test.yml up -d --wait` | Exit 0; `posture-test-postgres-1 Healthy`; `posture-test-mqtt-broker-1 Healthy`. |
| `python reports/e2e_full/tools/run_e2e_cli.py` | Schema catalog: PK `posture_events_pkey`, unique `posture_events_event_id_key`, CHECK label/confidence, indexes `idx_posture_events_ts`, `idx_posture_events_seat_ts`; `initial_rows=0`. 64 case PASS, 0 FAIL; xem JSONL và console bên dưới. |
| `python reports/e2e_full/tools/run_b4_seat33.py` | Input `TEST-` + 28 `X`: length 33; `row_count=0`; log `seat_id must be a 1-32 character location code`; cleanup `remaining_rows=0`; stack test down. JSONL ghi B4-seat-33-exact. |
| `python -m pytest -q --ignore=tests/tmp49gc3lh9` | `136 passed, 3 skipped, 5 deselected in 12.46s`. Bỏ qua đúng thư mục bị lỗi quyền khi pytest collect. |

## Broker auth

| Lệnh | Output thực tế |
|---|---|
| `$env:RUN_MQTT_AUTH_INTEGRATION='1'; python -m pytest -q -rs -m integration tests/integration/test_mqtt_auth.py` | `1 skipped`; fixture báo authenticated Docker stack không start được. |
| `python reports/e2e_full/tools/auth_stack_probe.py` | `password_file_generation=PASS mode=0o666`; `compose_up_exit=1`; broker: `chown: ... Read-only file system`; `Error: Unable to open pwfile "/mosquitto/config/password_file"`; `Error opening password file ...`; `credential_leak_scan=NOT_FOUND in Compose startup output and broker logs`. Probe đã dừng stack auth và xóa thư mục credential tạm. |

## Lượt CLI E2E cuối

| Lệnh | Output / artifact |
|---|---|
| `python -m py_compile reports/e2e_full/tools/run_e2e_cli.py` | Exit 0. |
| `python reports/e2e_full/tools/run_e2e_cli.py *> reports/e2e_full/cli_run_console.txt` | Exit 0; 64 PASS, 0 FAIL trong ma trận chính. `cli_results.jsonl` ghi từng case, expected, actual và ID; `cli_run_console.txt` giữ transcript, `subscriber.log`, `api.log`, `dashboard.log` giữ log dịch vụ. |
| `python -B reports/e2e_full/tools/render_case_table.py` | Exit 0; sinh bảng chi tiết 65 case từ output JSONL trong `report.md`; không gọi dịch vụ. |
| `D API` trong helper: GET `/api/events/latest`, `/api/events` với các tham số/giá trị trong ID; POST/PUT/PATCH/DELETE `/api/events` và path lạ | Body/status/header/timing thực tế được lưu từng dòng trong `cli_results.jsonl`. Ví dụ: `405`, `Allow: GET`, `{"error": "Method not allowed"}`; DB down: `503`, `{"error": "Service temporarily unavailable"}`. |
| B7 dừng/khởi động DB test | Event 10 s: count 1, tổng phục hồi 13.39 s; event 30 s: count 1, tổng phục hồi 34.04 s; batch 50: 50 stored/0 duplicate/0 missing; subscriber offline: 4/4 stored. API DB-down trả 503 trong 2.013–2.025 s. |
| `docker compose -p posture-test -f docker-compose.test.yml down` | Exit 0; cả hai container test stopped/removed và network test removed; không dùng `-v`. |
| Xác minh sau cleanup bằng Docker inventory và TCP connect loopback | Không còn container/network test; port 15432, 11883, 15433, 11884, 18000, 18080 đều `CLOSED`; `.test-mqtt-auth` và `tools/__pycache__` không tồn tại. |

## Kiểm kê H và cleanup

- Đọc YAML `docker-compose.yml` bằng PyYAML: services `mqtt-broker`, `api`, `subscriber`, `postgres`, `dashboard`; mọi port mapping có host IP `127.0.0.1`. Đọc `mosquitto.conf`: anonymous false, password_file configured, không có `acl_file`.
- `docker ps -a --format 'table {{.Names}}\t{{.Status}}'` là read-only. Output có các container stack chính đang chạy, `classroom-posture-iot-backend Exited (137)`, `industrial-defect-postgres Exited (0)`. Không thao tác các container này.
- Cleanup trong helper dùng `DELETE ... WHERE event_id = ANY(%s)` với đúng list ID của run cuối; output `remaining_rows: 0`. List ID nằm trong `cli_results.jsonl` và transcript.
- Ma trận chính có 64 ca PASS; ca B4 seat đúng 33 ký tự chạy bổ sung PASS, tổng artifact JSONL là 65 ca PASS, 0 FAIL. Cleanup ma trận chính có 131 ID duy nhất (146 phần tử có lặp do ghi lại cùng ID cho cùng payload); ca bổ sung có 1 ID riêng và `remaining_rows: 0`.
- Có một CLI exploratory run đã cleanup thành công trước lượt lưu artifact cuối; ID list của run đó chỉ nằm trong tool terminal output và không được chép sang file này. Test DB được xác nhận rỗng sau cleanup, và container DB đã bị loại bỏ khi `down`.

## Lưu ý về lệnh không chạy

Không có lệnh browser, DevTools, screenshot hay MJPEG server giả vì năng lực màn hình không có trong phiên. Không chạy Compose project chính hoặc cổng 8000/8080/5433/1883.
