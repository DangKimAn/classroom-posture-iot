# Báo cáo kiểm thử E2E backend/dashboard

Ngày chạy: 2026-11-16 (UTC+07:00)  
Môi trường: Windows, PowerShell, Python 3.14, Docker Engine 29.9.2, Mosquitto 2.0.22, image PostgreSQL 16 Alpine. Browser/DevTools: không được cung cấp trong phiên.  
Phạm vi dữ liệu: dữ liệu tổng hợp, `seat_id` tiền tố `TEST-`, giả định mỗi ghế một người.

## Tóm tắt

**Kết quả: chưa ổn để đóng kiểm thử E2E toàn hệ thống.** Theo cách đếm từng dòng test: **69 PASS, 1 FAIL, 24 BLOCKED, 0 N/A**. Trong đó 65 PASS là ca ghi trong JSONL; thêm 4 kiểm tra riêng là healthcheck, schema/migration, kiểm kê cấu hình loopback và cleanup. FAIL là stack auth không khởi động. BLOCKED gồm C1–C4, E1–E11, F1–F7, phần GUI của G và ảnh Docker Desktop của H. Không có ca giao diện nào được đánh PASS.

### Bước kiểm tra khả năng

| Khả năng | Kết quả thực tế |
|---|---|
| (a) Chụp màn hình | Không có công cụ screenshot trong phiên. |
| (b) Mở và điều khiển trình duyệt | Không có công cụ browser/computer input trong phiên. |
| (c) DevTools Console/Network | Không có khả năng mở DevTools trong phiên. |
| (d) Terminal | Có; PowerShell và `functions.exec_command` chạy được. |

Vì thiếu (a), (b), (c), nhóm E và F được ghi BLOCKED theo yêu cầu. Nhóm D được thực hiện bằng HTTP CLI, không có ảnh. Nhóm G chỉ xác minh chuỗi MQTT → DB → API → HTTP proxy; phần hiển thị GUI bị BLOCKED.

## Khám phá hợp đồng và hệ thống

- Endpoint: `GET /api/events/latest` trả event mới nhất theo ghế; `GET /api/events` nhận `from`, `to`, `seat_id`, `limit`. Không có `/docs`, `/openapi.json`, `/swagger`, `/redoc`; cả bốn trả `404 {"error": "Not found"}` khi gọi CLI.
- Topic: `classroom/posture/events`.
- Payload yêu cầu `event_id`, `ts`, `seat_id`, `label`, `confidence`, `model`, `angles`; nhãn là `upright`, `slouching`, `leaning`, `unknown`; `seat_id` 1–32 ký tự thuộc `[A-Za-z0-9_-]`; confidence số hữu hạn 0–1; trunk góc hữu hạn hoặc `null` chỉ với nhãn `unknown`; payload tối đa 16,384 byte.
- API mặc định `limit=100`, tối đa 500; thời gian phải ISO-8601 UTC. API trả JSON fields `event_id`, `ts`, `seat_id`, `label`, `trunk_angle`, `confidence`, `model_version`.
- Bảng `posture_events`: PK `id`, unique `event_id`, CHECK nhãn/confidence; chỉ mục `idx_posture_events_ts` và `idx_posture_events_seat_ts`. Migration thực tế đã chạy và schema được introspect.
- Subscriber dùng client ID cố định `posture-backend`, `clean_session=False`, manual ACK, subscribe QoS 1. ACK chỉ sau khi ingest hoàn tất; lỗi storage tạm thời sau retry thì disconnect trước ACK. Retry ingest có 3 lần thử với delay 0.5 s và 1.0 s; vòng ngoài log reconnect chờ 3 s. Vision publisher dùng QoS 1, không retain.
- Dashboard source gọi latest và history mỗi chu kỳ 2 s, chặn request chồng nhau, gửi seat/time filters lên API cùng `limit=100`; giao diện chia trang 8 event. Đây là đọc code, chưa kiểm chứng trên trình duyệt. Do có hai fetch mỗi chu kỳ, mã nguồn dự kiến khoảng 10 HTTP request `/api` trong 10 giây (khoảng 5 chu kỳ × 2; có thể khoảng 12 nếu phép đếm tính cả refresh tức thời lúc tải trang), khác với giả định “khoảng 5 request” nếu đếm từng request.
- Preview camera dùng trực tiếp `img.src`, chỉ cho URL HTTP không có user/password; source không gửi frame lên `/api`. Runtime F chưa kiểm tra.

Nguồn chính: [contract](../../backend/domain/contract.py), [validator](../../backend/domain/validator.py), [query rules](../../backend/domain/query.py), [HTTP API](../../backend/interfaces/http_api.py), [subscriber](../../backend/interfaces/mqtt_consumer.py), [ingest retry](../../backend/services/ingest_service.py), [migration](../../backend/migrations/001_create_posture_events.sql), [dashboard JS](../../web/app.js), [dashboard server](../../web/app_web.py), [README backend](../../backend/README.md), [README web](../../web/README.md).

## Kết quả A–D

Kết quả từng ca CLI, input/expected/actual và `event_id` được lưu theo dòng trong [cli_results.jsonl](cli_results.jsonl); output terminal và log tiến trình nằm ở [cli_run_console.txt](cli_run_console.txt), [subscriber.log](subscriber.log), [api.log](api.log), [dashboard.log](dashboard.log). Expected được xác định từ các nguồn nêu trên trước khi gửi từng nhóm request.

Nguồn expected theo nhóm: A1 `docker-compose.test.yml:2-30`; A2 `backend/migrations/001_create_posture_events.sql:1-12`; A3 `backend/api.py:10-18`, `backend/infrastructure/migrations.py:11-20`; B1–B4 `backend/domain/contract.py:3-12`, `backend/domain/validator.py:13-74`; B2 `backend/repositories/event_repository.py:28-46`; B6–B7 `backend/interfaces/mqtt_consumer.py:23-68,80-138`, `backend/services/ingest_service.py:31-70`; D `backend/domain/query.py:10-46`, `backend/interfaces/http_api.py:38-103`, `backend/config.py:13,94-99`, `web/app_web.py:33-114`. Dùng output JSONL theo ID để xem input, expected, actual và ID cụ thể.

| ID | Cách / INPUT | OUTPUT MONG ĐỢI (nguồn) | OUTPUT THỰC TẾ | Kết quả |
|---|---|---|---|---|
| A1 | Compose test riêng; PostgreSQL và broker | Cả hai healthy theo healthcheck trong `docker-compose.test.yml` | `posture-test-postgres-1 Healthy`; `posture-test-mqtt-broker-1 Healthy` | PASS |
| A2 | Chạy migration, đọc catalog PostgreSQL | PK, unique event ID, CHECK nhãn/confidence, hai index theo migration | Cột, constraint và index đúng như mô tả; DB trước test có 0 hàng | PASS |
| A3 | Gọi API khi DB dừng | `api.main` chạy migration trước HTTP server; nếu DB không sẵn sàng thì startup không mở server (`backend/api.py`, migrations) | Process exit 1; cuối traceback: `psycopg.errors.ConnectionTimeout: connection timeout expired` | PASS (hành vi theo code) |
| B1 | Publish bốn nhãn, bốn ghế `TEST-*` | Mỗi ID có 1 dòng; API history chứa các ID | 4/4 DB count = 1; API có đủ cả 4 ID | PASS |
| B2 | Publish lại cùng event ID | Unique constraint/dedup, vẫn 1 dòng | DB count = 1; subscriber log `duplicate event ignored` | PASS |
| B3 | `unknown/null`, nhãn khác/null, confidence 0/1, seat 32 ký tự; unit seat 1 ký tự | Validator rules trong `validator.py` | Các biên hợp lệ có count 1; `upright/null` bị từ chối với `angles.trunk may be null only when label is unknown`; seat một ký tự unit-only trả `valid=True`, không publish/ghi DB | PASS |
| B4 | 17 message lỗi/không đúng topic; UUID lỗi có input `not-a-uuid`; chuỗi mang nhãn `seat-33` ở lượt này thực tế 34 ký tự | Mọi payload sai không ghi DB; subscriber sống (`backend/domain/contract.py:6`, `backend/domain/validator.py:13-74`) | 17 gửi; 15 ID hợp lệ truy vấn được có count 0; subscriber vẫn chạy. Ca 33 ký tự chính xác được gửi bổ sung riêng như dòng kế tiếp. | PASS, có bổ sung đầu vào |
| B4-seat-33-exact | Một event `TEST-` + 28 ký tự `X` (33 ký tự tổng cộng) | Từ chối seat dài hơn 32 (`validator.py`) | `seat_length=33`, DB count 0, log `seat_id must be a 1-32 character location code`; ID được lưu trong JSONL | PASS |
| B5 | Batch 50 message hợp lệ, timestamp tăng dần | Đủ 50 dòng; API trả mới nhất trước | `stored_count=50`, 0 thiếu; 50 ID đầu của history khớp batch đảo ngược; API trả 58 event tổng | PASS |
| B6 | Restart broker, publish event mới | Subscriber subscribe lại và lưu event | ID mới count 1; thời gian từ restart tới lưu **2.672 s**; log có disconnect rồi `ready; subscribed topic=...` | PASS |
| B7-i | DB dừng 10 s, publish QoS 1 trước khi khởi động lại DB | Retry hữu hạn, disconnect trước ACK; persistent session giữ bản tin chưa ACK khi broker còn chạy | Sau outage 10 s, event count 1; tổng phục hồi 13.39 s; log `storage unavailable after retries: ConnectionTimeout`, disconnect và reconnect | PASS, không mất event quan sát được |
| B7-ii | DB dừng 30 s, publish QoS 1 | Như B7-i | Sau outage 30 s, event count 1; tổng phục hồi 34.04 s | PASS, không mất event quan sát được |
| B7-iii | DB dừng, publish batch 50 | Tin QoS 1 chưa ACK được broker giữ trong session đang chạy; sau DB recovery lưu mỗi ID một lần | 50/50 lưu, duplicate 0, missing 0 | PASS |
| B7-iv | Dừng subscriber, gửi 4 QoS 1, khởi động lại cùng client ID | Session `clean_session=False` nhận queue sau khi subscriber lên lại | 4/4 count = 1; subscriber log xác nhận subscribe lại | PASS |
| D API | GET latest/history rỗng và có dữ liệu; limit 1/100/500 và lỗi 0/-1/501/abc/rất lớn; seat có/không có/sai hoa thường/rỗng/quá dài; UTC from/to, range ngược, thiếu timezone, format sai, offset; POST/PUT/PATCH/DELETE và URL lạ; docs routes | Status/body theo `http_api.py` và `query.py`; `Allow: GET`; DB lỗi trả 503 generic | Các subcase D được ghi riêng trong JSONL. 200 JSON; invalid query `400 {"error": "Invalid query parameters"}`; known path method khác GET `405 {"error": "Method not allowed"}`, `Allow: GET`; unknown path `404 {"error": "Not found"}`; DB down `503 {"error": "Service temporarily unavailable"}` trong 2.013–2.025 s; sau recovery 200. `seat_id` phân biệt hoa thường. | PASS cho ca đã liệt kê trong JSONL |
| D static/proxy | Local `web/app_web.py` port 18080: `/`, path lạ, `/api/events/latest`; API dừng/DB dừng | Static 200/404, proxy chuyển tiếp status upstream hoặc trả 502 khi API không chạy (`app_web.py`) | `/` 200 `text/html` (7,654 ký tự); path lạ 404; API proxy 200 `[]`; API dừng proxy 502 HTML `Backend is unavailable`; DB dừng proxy giữ 503 JSON | PASS |

Lệch đầu vào đã phát hiện sau lượt đầu: helper ban đầu gắn nhãn `seat-33` cho `TEST-` + 29 ký tự (`34` ký tự tổng). Ca này vẫn là input quá dài nhưng không chứng minh biên 33. Đã gửi bổ sung payload đúng 33 ký tự qua broker/subscriber/DB, có output và event ID riêng trong JSONL; helper hiện đã chỉnh về 28 ký tự sau tiền tố.

**Giới hạn phạm vi D:** Các thao tác API được chạy qua HTTP CLI như hướng dẫn fallback khi không có GUI; không có browser screenshot. Không thực hiện mọi tổ hợp tham số có thể có ngoài các ca được ghi trong JSONL.

## Nhóm C — broker xác thực

File auth compose tồn tại nên nhóm C không phải N/A. Fixture tạo credential ngẫu nhiên và không in ra, nhưng stack không khởi động được. Probe độc lập ghi:

- `password_file_generation=PASS`, file bind có mode báo cáo `0o666` (không đọc nội dung).
- Compose auth exit 1; broker log: `chown: /mosquitto/config/password_file: Read-only file system`, `chown: /mosquitto/config/mosquitto-test-auth.conf: Read-only file system`, `Error: Unable to open pwfile "/mosquitto/config/password_file".`, `Error opening password file "/mosquitto/config/password_file".`
- Quét credential ngẫu nhiên trong output Compose và broker log: `NOT_FOUND`. API/subscriber không chạy trên auth stack, do đó quét leak C4 chưa bao phủ những nguồn đó.

| ID | Kết quả |
|---|---|
| C0 auth stack startup | FAIL — broker không mở password file read-only. |
| C1 đúng credential | BLOCKED — broker không healthy. |
| C2 sai mật khẩu/tên/anonymous và đếm retry | BLOCKED — broker không healthy. |
| C3 broker restart auth | BLOCKED — broker không healthy. |
| C4 leak toàn bộ log/API/UI | BLOCKED một phần — chỉ startup output và broker log được quét, không có API/subscriber/UI auth để kiểm tra. |

## Nhóm E–G

| Nhóm | Kết quả | Lý do / quan sát tĩnh |
|---|---|---|
| E1–E11 dashboard GUI | BLOCKED toàn bộ | Không thể mở/điều khiển browser, Console/Network hoặc chụp ảnh. Không bịa ảnh/kết quả. Source cho thấy 2 fetch mỗi chu kỳ; filters gửi đến API trước limit 100; pagination 8; seat render bằng `textContent`; trạng thái API lấy từ response. Các điểm này chưa được xác minh bằng GUI. |
| F1–F7 camera preview | BLOCKED toàn bộ | Không có browser để nhập URL, quan sát stream/Network/DOM. Không dựng ảnh hay giả lập kết quả. Source cho thấy preview đặt URL trực tiếp vào `img.src`, `stopCamera` bỏ `src`, chỉ chấp nhận HTTP và không gọi API gửi frame; chưa có runtime evidence. |
| G backend/API | PASS một phần | MQTT → DB → API và HTTP proxy đã quan sát bằng CLI. |
| G dashboard trực quan | BLOCKED | Không có GUI và không có screenshot. |

## H — cấu hình stack chính và inventory (chỉ đọc)

- YAML cho thấy services `mqtt-broker`, `api`, `subscriber`, `postgres`, `dashboard`; mọi published port đều có host IP `127.0.0.1` (1883, 9001, API `${PORT:-8000}`, DB `${POSTGRES_PORT:-5433}`, dashboard 8080).
- Broker config: `allow_anonymous false`; có `password_file`; không có `acl_file`.
- `docker ps -a` (chỉ đọc) cho thấy các container stack chính đang chạy. Hai container đã dừng được thấy: `classroom-posture-iot-backend` (Exited 137) và `industrial-defect-postgres` (Exited 0). Không xóa hay restart container nào trong inventory.
- Không thể chụp màn hình Docker Desktop; inventory ở trên là output CLI, không phải ảnh giao diện.

## Lỗi và mức độ

| ID | Mức | Tái hiện / expected / actual | Vị trí nghi ngờ |
|---|---|---|---|
| C0 | P2 | Chạy auth compose với password file vừa sinh và bind read-only. Expected broker healthy để kiểm thử auth; actual container thoát 13 và Mosquitto không mở được password file. | `docker-compose.test.auth.yml` mount password file dưới `/mosquitto/config`; entrypoint image cố `chown` mount read-only. Chỉ ghi nhận, không sửa code theo phạm vi chỉ kiểm thử. |
| E1 expectation | P3 (đề xuất chỉnh checklist) | Checklist kỳ vọng khoảng 5 request `/api`/10s; source gọi latest và history mỗi 2s, tương đương khoảng 10–12 request/10s nếu đếm request HTTP riêng và tính refresh tức thời. Chưa xác minh bằng Network. | `web/app.js` phần `refresh()` và `setInterval`. |

Không quan sát thấy mất event trong bốn kịch bản B7 khi broker test vẫn chạy. Broker test đặt `persistence false`; không thử tình huống broker restart khi subscriber offline/DB vẫn down, nên không kết luận về độ bền queue qua broker restart. Không có bằng chứng về lỗi P1 mất dữ liệu trong các ca đã chạy.

## Dọn dẹp

- Helper xóa chính xác các event ID của lượt CLI cuối; kết quả `remaining_rows: 0`. Toàn bộ ID từng gửi/đưa vào payload của lượt này được lưu trong [cli_results.jsonl](cli_results.jsonl) và [cli_run_console.txt](cli_run_console.txt), kể cả các ID invalid có thể truy vấn.
- Dừng API, dashboard và subscriber local; kiểm tra port local sau khi kết thúc. Không chạy mock MJPEG server.
- Dừng stack test bằng `docker compose -p posture-test -f docker-compose.test.yml down` (không có `-v`); output xác nhận hai container và network test đã removed. Không thao tác stack chính.
- Probe auth cũng tự chạy `down` và xóa `.test-mqtt-auth`; thư mục không còn tồn tại.
- Một lượt CLI thăm dò trước khi hoàn tất artifact kết thúc bằng cleanup và `remaining_rows: 0`; danh sách ID của lượt thăm dò nằm trong terminal tool output trước đó, không được lưu lại vào artifact. Danh sách ID đầy đủ và có thể kiểm tra của lượt báo cáo cuối nằm trong JSONL nêu trên. Không còn DB test sau khi stack được dừng.

## Đề xuất theo ưu tiên

1. **P2:** Sửa cách cung cấp password file cho Mosquitto test trên Windows/Docker Desktop để broker chạy được dù config/password file được mount read-only; sau đó chạy lại C1–C4 và quét leak đầy đủ.
2. **P2:** Chạy lại E1–E11, F1–F7, G trên phiên có browser, DevTools và screenshot thật; lưu ảnh từng ca. Không dùng kết quả source review thay runtime evidence.
3. **P3:** Điều chỉnh tiêu chí E1 để đếm request phù hợp với hai endpoint fetch mỗi chu kỳ, hoặc ghi rõ đo chu kỳ polling thay vì số request.
4. Bổ sung B7 thử broker restart trong lúc subscriber offline và message QoS 1 đang chờ; test hiện tại chỉ xác minh broker restart khi subscriber active.

## Kết luận giới hạn

Các kết quả chỉ áp dụng cho dữ liệu tổng hợp và giả định mỗi ghế một người. Chưa dùng camera/lớp học thật; không kết luận độ chính xác model, độ trễ camera hoặc hiệu năng thực địa. Nhiệm vụ này không sửa mã nguồn, không tạo nhánh, không commit/push; stack chính chỉ được kiểm kê read-only.


<!-- PER_CASE_TABLE_START -->
### Bảng từng test case CLI

Expected được ghi cố định trong helper trước khi chạy. Body/ID dài được lưu nguyên vẹn trong `cli_results.jsonl`; bảng rút gọn chỉ để dễ đọc.

| ID | Cách / INPUT | OUTPUT MONG ĐỢI (nguồn) | OUTPUT THỰC TẾ | Kết quả |
|---|---|---|---|---|
| D-empty-latest | HTTP CLI to local API; empty-latest | 200 JSON [] — `backend/interfaces/http_api.py:38-103`; `backend/domain/query.py:32-46` | `{"status":200,"content_type":"application/json; charset=utf-8","body":"[]","seconds":0.083}` | PASS |
| D-empty-history | HTTP CLI to local API; empty-history | 200 JSON [] — `backend/interfaces/http_api.py:38-103`; `backend/domain/query.py:32-46` | `{"status":200,"content_type":"application/json; charset=utf-8","body":"[]"}` | PASS |
| D-docs-docs | HTTP CLI to local API; docs-docs | 404 JSON — `backend/interfaces/http_api.py:38-103` | `{"status":404,"body":"{\"error\": \"Not found\"}"}` | PASS |
| D-docs-openapi.json | HTTP CLI to local API; docs-openapi.json | 404 JSON — `backend/interfaces/http_api.py:38-103` | `{"status":404,"body":"{\"error\": \"Not found\"}"}` | PASS |
| D-docs-swagger | HTTP CLI to local API; docs-swagger | 404 JSON — `backend/interfaces/http_api.py:38-103` | `{"status":404,"body":"{\"error\": \"Not found\"}"}` | PASS |
| D-docs-redoc | HTTP CLI to local API; docs-redoc | 404 JSON — `backend/interfaces/http_api.py:38-103` | `{"status":404,"body":"{\"error\": \"Not found\"}"}` | PASS |
| D-limit-1 | HTTP CLI to local API; limit-1 | 200 array and no more than limit rows — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":200,"rows":0}` | PASS |
| D-limit-100 | HTTP CLI to local API; limit-100 | 200 array and no more than limit rows — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":200,"rows":0}` | PASS |
| D-limit-500 | HTTP CLI to local API; limit-500 | 200 array and no more than limit rows — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":200,"rows":0}` | PASS |
| D-limit-invalid-0 | HTTP CLI to local API; limit-invalid-0 | 400 JSON — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":400,"body":"{\"error\": \"Invalid query parameters\"}"}` | PASS |
| D-limit-invalid--1 | HTTP CLI to local API; limit-invalid--1 | 400 JSON — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":400,"body":"{\"error\": \"Invalid query parameters\"}"}` | PASS |
| D-limit-invalid-501 | HTTP CLI to local API; limit-invalid-501 | 400 JSON — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":400,"body":"{\"error\": \"Invalid query parameters\"}"}` | PASS |
| D-limit-invalid-abc | HTTP CLI to local API; limit-invalid-abc | 400 JSON — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":400,"body":"{\"error\": \"Invalid query parameters\"}"}` | PASS |
| D-limit-invalid-999999999999999999999999999999 | HTTP CLI to local API; limit-invalid-999999999999999999999999999999 | 400 JSON — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":400,"body":"{\"error\": \"Invalid query parameters\"}"}` | PASS |
| D-seat-invalid-0 | HTTP CLI to local API; seat-invalid-0 | 400 JSON — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":400,"body":"{\"error\": \"Invalid query parameters\"}"}` | PASS |
| D-seat-invalid-33 | HTTP CLI to local API; seat-invalid-33 | 400 JSON — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":400,"body":"{\"error\": \"Invalid query parameters\"}"}` | PASS |
| D-unknown-param | HTTP CLI to local API; unknown-param | 400 JSON — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":400,"body":"{\"error\": \"Invalid query parameters\"}"}` | PASS |
| D-time-utc-from | HTTP CLI to local API; time-utc-from | 200 — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":200,"body":"[]"}` | PASS |
| D-time-utc-to | HTTP CLI to local API; time-utc-to | 200 — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":200,"body":"[]"}` | PASS |
| D-time-utc-equal | HTTP CLI to local API; time-utc-equal | 200 — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":200,"body":"[]"}` | PASS |
| D-time-from-after-to | HTTP CLI to local API; time-from-after-to | 400 — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":400,"body":"{\"error\": \"Invalid query parameters\"}"}` | PASS |
| D-time-no-timezone | HTTP CLI to local API; time-no-timezone | 400 — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":400,"body":"{\"error\": \"Invalid query parameters\"}"}` | PASS |
| D-time-bad-time | HTTP CLI to local API; time-bad-time | 400 — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":400,"body":"{\"error\": \"Invalid query parameters\"}"}` | PASS |
| D-method-POST | HTTP CLI to local API; method-POST | 405 JSON, Allow: GET — `backend/interfaces/http_api.py:38-103` | `{"status":405,"allow":"GET","body":"{\"error\": \"Method not allowed\"}"}` | PASS |
| D-method-unknown-POST | HTTP CLI to local API; method-unknown-POST | 404 JSON — `backend/interfaces/http_api.py:38-103` | `{"status":404,"body":"{\"error\": \"Not found\"}"}` | PASS |
| D-method-PUT | HTTP CLI to local API; method-PUT | 405 JSON, Allow: GET — `backend/interfaces/http_api.py:38-103` | `{"status":405,"allow":"GET","body":"{\"error\": \"Method not allowed\"}"}` | PASS |
| D-method-unknown-PUT | HTTP CLI to local API; method-unknown-PUT | 404 JSON — `backend/interfaces/http_api.py:38-103` | `{"status":404,"body":"{\"error\": \"Not found\"}"}` | PASS |
| D-method-PATCH | HTTP CLI to local API; method-PATCH | 405 JSON, Allow: GET — `backend/interfaces/http_api.py:38-103` | `{"status":405,"allow":"GET","body":"{\"error\": \"Method not allowed\"}"}` | PASS |
| D-method-unknown-PATCH | HTTP CLI to local API; method-unknown-PATCH | 404 JSON — `backend/interfaces/http_api.py:38-103` | `{"status":404,"body":"{\"error\": \"Not found\"}"}` | PASS |
| D-method-DELETE | HTTP CLI to local API; method-DELETE | 405 JSON, Allow: GET — `backend/interfaces/http_api.py:38-103` | `{"status":405,"allow":"GET","body":"{\"error\": \"Method not allowed\"}"}` | PASS |
| D-method-unknown-DELETE | HTTP CLI to local API; method-unknown-DELETE | 404 JSON — `backend/interfaces/http_api.py:38-103` | `{"status":404,"body":"{\"error\": \"Not found\"}"}` | PASS |
| D-get-unknown | HTTP CLI to local API; get-unknown | 404 JSON — `backend/interfaces/http_api.py:38-103` | `{"status":404,"body":"{\"error\": \"Not found\"}"}` | PASS |
| D-static-root | HTTP CLI to local dashboard/proxy; static-root | 200 — `web/app_web.py:33-114` | `{"status":200,"content_type":"text/html","body_chars":7654}` | PASS |
| D-static-rootno-such-file | HTTP CLI to local dashboard/proxy; static-rootno-such-file | 404 — `web/app_web.py:33-114` | `{"status":404,"content_type":"text/html;charset=utf-8","body_chars":460}` | PASS |
| D-dashboard-api-proxy | HTTP CLI to local dashboard/proxy; dashboard-api-proxy | 200 JSON [] — `web/app_web.py:33-114` | `{"status":200,"body":"[]"}` | PASS |
| B1-four-labels | MQTT QoS 1 → subscriber → PostgreSQL/API; B 1-four-labels | 4 stored rows and the API contains all 4 IDs — `backend/domain/contract.py:3-12`; `backend/domain/validator.py:13-74`; `backend/repositories/event_repository.py:28-46` | `{"status":200,"ids":["7908005f-e9e7-453c-a4ce-d3ae3bb22dd4","4ce23a52-2689-4547-a9ac-071f80bb61a5","48b05225-1cb3-4785-ba2e-75d48257e8ac","0718bffb-b7fe-4d1f-b64e-fc08043d6b05"],"db_counts":[1,1,1,1],"api_contains_all":true}` | PASS |
| D-seat-existing | HTTP CLI to local API; seat-existing | 200 and 1 matching history rows — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":200,"rows":1,"body":"[{\"event_id\": \"4ce23a52-2689-4547-a9ac-071f80bb61a5\", \"ts\": \"2026-11-16T14:41:28.410997Z\", \"seat_id\": \"TEST-A02\", \"label\": \"slouching\", \"trunk_angle\": 24.0, \"confidence\": 0.9, \"model_version\": \"synthetic-e2e\"}]"}` | PASS |
| D-seat-case-sensitive | HTTP CLI to local API; seat-case-sensitive | 200 and 0 matching history rows — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":200,"rows":0,"body":"[]"}` | PASS |
| D-seat-unknown | HTTP CLI to local API; seat-unknown | 200 and 0 matching history rows — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":200,"rows":0,"body":"[]"}` | PASS |
| B2-duplicate | MQTT QoS 1 → subscriber → PostgreSQL/API; B 2-duplicate | one DB row after same event_id is published twice — `backend/domain/contract.py:3-12`; `backend/domain/validator.py:13-74`; `backend/repositories/event_repository.py:28-46` | `{"event_id":"f4073369-17e6-4226-bc82-8d2775eaf858","rows":1}` | PASS |
| B3-seat-one-unit | Python unit; validator only, no DB; B 3-seat-one-unit | validate_event_payload accepts one character; no DB write — `backend/domain/contract.py:3-12`; `backend/domain/validator.py:13-74`; `backend/repositories/event_repository.py:28-46` | `{"valid":true,"reason":""}` | PASS |
| B3-boundaries | MQTT QoS 1 → subscriber → PostgreSQL/API; B 3-boundaries | unknown/null and confidence endpoints accepted; non-unknown/null rejected; 32-char seat accepted — `backend/domain/contract.py:3-12`; `backend/domain/validator.py:13-74`; `backend/repositories/event_repository.py:28-46` | `{"accepted_ids":["a82ce9cd-b9cc-4d25-95f8-af63785c0f57","0759481f-18fd-4753-8522-eab265ad293d","a37e3f9d-2637-41d5-9d57-96dbcb862392"],"accepted_counts":[1,1,1],"non_unknown_null_valid":false,"reason":"angles.trunk may be null only when label is unknown","rejected_count":0}` | PASS |
| B4-invalid-17 | MQTT QoS 1 → subscriber → PostgreSQL/API; MQTT payload cases: missing, extra, bad-uuid, timezone, seat-empty, seat-33, label, confidence-1.5, confidence-negative, confidence-true, confidence-string, angle-nan, angle-infinity, malformed-json, empty, oversize, wrong-topic | 17 invalid/irrelevant MQTT messages create no rows and subscriber remains alive — `backend/domain/contract.py:3-12`; `backend/domain/validator.py:13-74`; `backend/repositories/event_repository.py:28-46` | `{"sent":17,"cases":["missing","extra","bad-uuid","timezone","seat-empty","seat-33","label","confidence-1.5","confidence-negative","confidence-true","confidence-string","angle-nan","angle-infinity","malformed-json","empty","oversize","wrong-topic"],"event_ids":["61e49f4d-6ab4-4bd5-be41-ec60e580b561","91f609ad-2e2f-436d-9231-65f76836f333","0703c714-0171-473a-813a-556dbe46d4f9","deb73b5e-a16c-4d80-80f8-4e640c0bc992","13… (full actual body/IDs in cli_results.jsonl)` | PASS |
| B5-batch-50 | MQTT QoS 1 → subscriber → PostgreSQL/API; B 5-batch-50 | 50 rows stored; latest-first API order — `backend/domain/contract.py:3-12`; `backend/domain/validator.py:13-74`; `backend/repositories/event_repository.py:28-46` | `{"status":200,"stored_count":50,"first_50_match_descending_batch":true,"returned_rows":58}` | PASS |
| D-limit-1-populated | HTTP CLI to local API; limit-1-populated | 200 and at most 1 rows — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":200,"rows":1}` | PASS |
| D-limit-100-populated | HTTP CLI to local API; limit-100-populated | 200 and at most 100 rows — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":200,"rows":58}` | PASS |
| D-limit-500-populated | HTTP CLI to local API; limit-500-populated | 200 and at most 500 rows — `backend/domain/query.py:10-46`; `backend/interfaces/http_api.py:72-103` | `{"status":200,"rows":58}` | PASS |
| B6-broker-restart | MQTT QoS 1 → subscriber → PostgreSQL/API; B 6-broker-restart | subscriber reconnects and stores post-restart event — `backend/domain/contract.py:3-12`; `backend/domain/validator.py:13-74`; `backend/repositories/event_repository.py:28-46` | `{"event_id":"d982fa25-9e38-4c16-8174-1829b493193b","row_count":1,"recovery_seconds":2.672}` | PASS |
| B7-db-outage-10s | MQTT QoS 1 → subscriber → PostgreSQL/API; B 7-db-outage-10s | QoS 1 unacked event is retried/re-delivered and stored once after DB recovery — `backend/services/ingest_service.py:31-70`; `backend/interfaces/mqtt_consumer.py:23-68,80-138` | `{"event_id":"5a14d316-304e-4885-a19c-06d7e74427fe","rows":1,"outage_seconds":10,"total_recovery_seconds":13.39}` | PASS |
| B7-db-outage-10s-api-503 | MQTT QoS 1 → subscriber → PostgreSQL/API; B 7-db-outage-10s-api-503 | 503 generic JSON while DB is stopped — `backend/services/ingest_service.py:31-70`; `backend/interfaces/mqtt_consumer.py:23-68,80-138` | `{"status":503,"body":"{\"error\": \"Service temporarily unavailable\"}","seconds":2.013}` | PASS |
| B7-db-outage-10s-proxy-503 | MQTT QoS 1 → subscriber → PostgreSQL/API; B 7-db-outage-10s-proxy-503 | dashboard API proxy preserves backend 503 — `backend/services/ingest_service.py:31-70`; `backend/interfaces/mqtt_consumer.py:23-68,80-138` | `{"status":503,"body":"{\"error\": \"Service temporarily unavailable\"}"}` | PASS |
| B7-db-outage-10s-api-startup-db-down | MQTT QoS 1 → subscriber → PostgreSQL/API; B 7-db-outage-10s-api-startup-db-down | startup migration fails fast before serving when DB is unavailable — `backend/services/ingest_service.py:31-70`; `backend/interfaces/mqtt_consumer.py:23-68,80-138` | `{"exit":1,"last_lines":["  File \"C:\\Users\\Admin\\AppData\\Local\\Programs\\Python\\Python314\\Lib\\site-packages\\psycopg\\connection.py\", line 126, in connect","    raise last_ex.with_traceback(None)","psycopg.errors.ConnectionTimeout: connection timeout expired"]}` | PASS |
| B7-db-outage-10s-api-recovered | MQTT QoS 1 → subscriber → PostgreSQL/API; B 7-db-outage-10s-api-recovered | API returns 200 after DB recovery — `backend/services/ingest_service.py:31-70`; `backend/interfaces/mqtt_consumer.py:23-68,80-138` | `{"status":200,"body_chars":12591}` | PASS |
| B7-db-outage-30s | MQTT QoS 1 → subscriber → PostgreSQL/API; B 7-db-outage-30s | QoS 1 unacked event is retried/re-delivered and stored once after DB recovery — `backend/services/ingest_service.py:31-70`; `backend/interfaces/mqtt_consumer.py:23-68,80-138` | `{"event_id":"bf4c55a1-9564-42e5-b5fc-d9c1bfa9b98a","rows":1,"outage_seconds":30,"total_recovery_seconds":34.04}` | PASS |
| B7-db-outage-30s-api-503 | MQTT QoS 1 → subscriber → PostgreSQL/API; B 7-db-outage-30s-api-503 | 503 generic JSON while DB is stopped — `backend/services/ingest_service.py:31-70`; `backend/interfaces/mqtt_consumer.py:23-68,80-138` | `{"status":503,"body":"{\"error\": \"Service temporarily unavailable\"}","seconds":2.025}` | PASS |
| B7-db-outage-30s-proxy-503 | MQTT QoS 1 → subscriber → PostgreSQL/API; B 7-db-outage-30s-proxy-503 | dashboard API proxy preserves backend 503 — `backend/services/ingest_service.py:31-70`; `backend/interfaces/mqtt_consumer.py:23-68,80-138` | `{"status":503,"body":"{\"error\": \"Service temporarily unavailable\"}"}` | PASS |
| B7-db-outage-30s-api-startup-db-down | MQTT QoS 1 → subscriber → PostgreSQL/API; B 7-db-outage-30s-api-startup-db-down | startup migration fails fast before serving when DB is unavailable — `backend/services/ingest_service.py:31-70`; `backend/interfaces/mqtt_consumer.py:23-68,80-138` | `{"exit":1,"last_lines":["  File \"C:\\Users\\Admin\\AppData\\Local\\Programs\\Python\\Python314\\Lib\\site-packages\\psycopg\\connection.py\", line 126, in connect","    raise last_ex.with_traceback(None)","psycopg.errors.ConnectionTimeout: connection timeout expired"]}` | PASS |
| B7-db-outage-30s-api-recovered | MQTT QoS 1 → subscriber → PostgreSQL/API; B 7-db-outage-30s-api-recovered | API returns 200 after DB recovery — `backend/services/ingest_service.py:31-70`; `backend/interfaces/mqtt_consumer.py:23-68,80-138` | `{"status":200,"body_chars":12800}` | PASS |
| B7-db-outage-batch-50 | MQTT QoS 1 → subscriber → PostgreSQL/API; B 7-db-outage-batch-50 | all 50 QoS 1 messages persist exactly once after DB recovery — `backend/services/ingest_service.py:31-70`; `backend/interfaces/mqtt_consumer.py:23-68,80-138` | `{"event_ids":["4748291b-fa82-4ace-b106-f0ad439812d2","0d21ea3e-4e2b-4ece-81b9-5235d2f324d7","cae2b7b9-cf06-4370-a9c7-7cb68fb6a963","60c123d0-c307-4080-878e-e65c1bb9ce0f","97302202-ddeb-4753-a82e-434d62152e44","23fb8374-48c6-48a3-94ce-2d49930e7cc0","f368a2b4-9bad-4f8f-bd73-47cb98f4cfab","fc7b32dc-7557-42cd-8503-6cd2a2f321d5","d1cc775b-567e-4845-a5cc-9a4a7dad95b3","4eaaade6-bfdc-4627-9c2e-e8892184a195","4a551d53-f295-4… (full actual body/IDs in cli_results.jsonl)` | PASS |
| B7-subscriber-offline-queue | MQTT QoS 1 → subscriber → PostgreSQL/API; B 7-subscriber-offline-queue | 4 QoS 1 messages stored once after same-client subscriber restarts — `backend/services/ingest_service.py:31-70`; `backend/interfaces/mqtt_consumer.py:23-68,80-138` | `{"event_ids":["47f02056-71f2-452c-8459-e390b611597f","7b011f82-8876-4a13-80cd-db98e03175a3","fb5ef956-451d-41d0-877b-284d85145c2c","ef9f9a57-8fb4-4abf-8448-d65a4a283b8e"],"rows":[1,1,1,1],"ready_after_restart":true}` | PASS |
| D-api-down-proxy | HTTP CLI to local API; api-down-proxy | 502 when local API is unavailable — `web/app_web.py:33-114` | `{"status":502,"body":"<!DOCTYPE HTML>\n<html lang=\"en\">\n    <head>\n        <meta charset=\"utf-8\">\n        <style type=\"text/css\">\n            :root {\n                color-scheme: light dark;\n            }\n        </style>\n        <title>Error response</title>\n    </head>\n    <body>\n        <h1>Error response</h1>\n        <p>Error code: 502</p>\n        <p>Message: Backend is unavailable.</p>\n     … (full actual body/IDs in cli_results.jsonl)` | PASS |
| D-api-recovery | HTTP CLI to local API; api-recovery | dashboard/API process returns 200 after API restart — `web/app_web.py:33-114` | `true` | PASS |
| D-latest-after-ingest | HTTP CLI to local API; latest-after-ingest | 200 JSON includes latest TEST events — `backend/interfaces/http_api.py:38-103`; `backend/domain/query.py:32-46` | `{"status":200,"content_type":"application/json; charset=utf-8","body":"[{\"event_id\": \"7908005f-e9e7-453c-a4ce-d3ae3bb22dd4\", \"ts\": \"2026-11-16T14:41:28.004895Z\", \"seat_id\": \"TEST-A01\", \"label\": \"upright\", \"trunk_angle\": 8.0, \"confidence\": 0.9, \"model_version\": \"synthetic-e2e\"}, {\"event_id\": \"4ce23a52-2689-4547-a9ac-071f80bb61a5\", \"ts\": \"2026-11-16T14:41:28.410997Z\", \"seat_id\": \"TEST… (full actual body/IDs in cli_results.jsonl)` | PASS |
| D-combined-filter | HTTP CLI to local API; combined-filter | 200 JSON array, seat/date/limit filters applied — `backend/interfaces/http_api.py:38-103`; `backend/domain/query.py:32-46` | `{"status":200,"body":"[{\"event_id\": \"4ce23a52-2689-4547-a9ac-071f80bb61a5\", \"ts\": \"2026-11-16T14:41:28.410997Z\", \"seat_id\": \"TEST-A02\", \"label\": \"slouching\", \"trunk_angle\": 24.0, \"confidence\": 0.9, \"model_version\": \"synthetic-e2e\"}]"}` | PASS |
| B4-seat-33-exact | MQTT QoS 1 → subscriber → PostgreSQL/API; B 4-seat-33-exact | 33-character seat_id rejected; DB count 0 — `backend/domain/contract.py:3-12`; `backend/domain/validator.py:13-74`; `backend/repositories/event_repository.py:28-46` | `{"event_id":"fb2b4136-1e19-4ecb-ac87-606c8e42ee9c","seat_length":33,"row_count":0,"log":"[mqtt] rejected message: seat_id must be a 1-32 character location code"}` | PASS |
<!-- PER_CASE_TABLE_END -->

## Addendum — kiểm tra độ bền hàng đợi broker (2026-11-17)

Chạy lại riêng P1–P5 bằng lệnh:

```powershell
$env:RUN_MQTT_AUTH_INTEGRATION = '1'
python -m pytest -q -s -m integration tests/integration/test_mqtt_auth.py -k persistent_session_queue
Remove-Item Env:RUN_MQTT_AUTH_INTEGRATION
```

Kết quả: **1 passed, 1 deselected, 292.02 giây**. Fixture dùng credential ngẫu nhiên trong tiến trình, project Compose riêng và volume Mosquitto riêng; không dùng stack chính. Event ID được ghi vào file tạm trước khi publish. Sau khi test kết thúc, không còn container/volume của project auth test, thư mục `.test-mqtt-auth` hoặc file JSONL event ID tạm.

Các tổng PASS/FAIL/BLOCKED và bảng C0–C4 ở phần trên là snapshot của lượt E2E ban đầu, không được tính lại trong addendum này. C0–C5 đã được chạy thành công trong lượt auth integration riêng ngày 2026-11-16; lượt ngày 2026-11-17 chỉ chạy P1–P5. Không dùng tổng lịch sử ở đầu báo cáo làm tổng mới nhất của mọi lượt test.

| Ca | Kết quả thực tế | Diễn giải |
|---|---|---|
| P1 — restart bình thường khi subscriber offline | 5/5 event được lưu, mỗi event một lần | Hàng đợi/session sống sót qua restart bình thường trong điều kiện test. |
| P2 — hard kill ngay sau publish | 0/5 event được lưu; `publish_seconds=0.018`, `restart_seconds=14.391` | Tái hiện mất hàng đợi chưa autosave. Đây là phép đo đặc tính; không tính là PASS về độ bền. |
| P3 — hard kill sau khi chờ autosave | 5/5 event được lưu, mỗi event một lần | Hàng đợi đã autosave sống sót qua hard kill trong lần chạy này. |
| P4 — Compose `down`/`up`, giữ volume | 5/5 event được lưu, mỗi event một lần | Named volume giữ session/hàng đợi qua việc tạo lại container. |
| P5 — Compose `down -v` trên project auth test | 0/5 event cũ được lưu; subscriber/session mới tiếp tục nhận event mới | Xóa volume test xóa session và hàng đợi đã lưu; không thao tác `down -v` trên project chính. |

Stack test dùng cấu hình persistence tương ứng với cấu hình đã đọc của broker chính: `persistence true`, `/mosquitto/data/`, `autosave_interval 30` và `max_queued_messages 10000`. Bằng chứng này là trên broker test cô lập, không phải hard-kill trực tiếp broker chính. Cấu hình chính và D-10 không bị sửa.

### Các phương án cần nhóm cân nhắc

1. **Giảm `autosave_interval`:** có thể rút ngắn khoảng trạng thái chưa autosave; đổi lại tăng tần suất ghi persistence. Không đảm bảo mất bằng 0 và vẫn cần hard-kill test trên cấu hình test mới.
2. **Yêu cầu dừng broker có kiểm soát khi bảo trì:** phù hợp với P1/P4 đã quan sát, nhưng không bảo vệ khi process/host chết đột ngột.
3. **Bổ sung durable outbox/replay phía publisher:** giữ event ID và gửi lại sau khởi động; phạm vi ảnh hưởng Vision và backend, cần thiết kế retry/dedup và duyệt riêng trước khi làm.
4. **Chấp nhận và tài liệu hóa cửa sổ rủi ro hiện tại:** chỉ phù hợp nếu nhóm xác nhận mức mất event này chấp nhận được cho demo. P2/P3 mới chứng minh hai thời điểm thử, chưa đo chính xác ranh giới theo từng giây quanh autosave.

Không chọn phương án hoặc sửa cấu hình broker chính vì D-10 vẫn `OPEN`. Nhóm cần chốt yêu cầu mất dữ liệu tối đa trước khi mở issue triển khai.

### Ghi chú môi trường

Docker Desktop không chạy lúc bắt đầu lượt. Khi khởi động Docker Desktop để chạy test cô lập, danh sách container sau đó cho thấy `iot_posture_mqtt` đã khởi động lại và có uptime khoảng 3 phút. Không gửi lệnh trực tiếp tới container chính, không đọc credential hay dữ liệu event của stack chính. Đây là dấu hiệu restart cùng lúc Docker engine lên; không có kiểm tra log riêng để xác định nguyên nhân chính xác.


## Addendum — kết quả auth, độ bền hàng đợi và giới hạn kiểm chứng (2026-11-17)

Tổng lịch sử ở đầu báo cáo (**69 PASS, 1 FAIL, 24 BLOCKED**) là snapshot của lượt E2E ban đầu và được giữ nguyên. Các lượt auth và queue dưới đây chạy riêng, không cộng vào tổng lịch sử.

### MQTT auth C1–C5

Lượt auth integration ngày 2026-11-16 được ghi nhận thành công. Các kết quả dưới đây tóm tắt assertion trong `tests/integration/test_mqtt_auth.py`; không có artifact riêng cho từng ca trong thư mục kết quả E2E.

| Ca | Kết quả | Bằng chứng |
|---|---|---|
| C1 — credential hợp lệ | PASS | Publisher Vision xác thực; subscriber lưu event một lần và API trả event. |
| C2 — sai mật khẩu, username lạ, anonymous | PASS | Cả ba kiểu truy cập bị từ chối; subscriber thử lại **5 lần trong 30 giây**. |
| C3 — broker restart | PASS | Subscriber kết nối và subscribe lại; event sau restart được lưu một lần. |
| C4 — kiểm tra rò rỉ | PASS | Test quét broker/subscriber log, API output/error, settings repr và caplog; không ghi credential vào báo cáo. |
| C5 — Vision dùng auth sai | PASS | Publisher không ở trạng thái connected; log, exception và repr không làm lộ credential. |

### MQTT queue P1–P5

Lượt queue integration ngày 2026-11-17 chạy riêng trên broker test cô lập. Broker test dùng `persistence true`, `/mosquitto/data/`, `autosave_interval 30` giây và `max_queued_messages 10000`, tương ứng cấu hình persistence đã đọc của broker chính. Đây **không phải** hard-kill test trên stack chính.

| Ca | Kết quả thực tế | Diễn giải |
|---|---|---|
| P1 — restart broker bình thường khi subscriber offline | 5/5 event được lưu | Hàng đợi sống sót trong điều kiện restart bình thường của test. |
| P2 — hard kill ngay sau publish | **0/5 event được lưu**; publish 0.018 giây, restart 14.391 giây | Event chưa autosave bị mất trong lần thử này. Đây là rủi ro mất dữ liệu, không phải PASS về durability. |
| P3 — hard kill sau autosave | 5/5 event được lưu | Hàng đợi đã autosave sống sót trong lần thử này. |
| P4 — Compose down/up, giữ volume | 5/5 event được lưu | Session và hàng đợi còn trong volume test. |
| P5 — Compose down -v trên project test | 0/5 event cũ được lưu | Xóa volume test làm mất session/hàng đợi đã lưu, như dự kiến. |

Không dùng kết quả này để kết luận stack chính đã vượt qua hard-kill test. D-10 về QoS/retain/độ bền còn OPEN; chưa sửa persistence/autosave của stack chính. Các phương án cần nhóm quyết định vẫn được ghi ở addendum queue phía trên.

### Đối chiếu finding Vision và giới hạn runtime

- Callback Paho phiên bản 2: đã khắc phục/chưa tái hiện trong source và test callback hiện tại.
- Validation số của `build_event`: đã khắc phục/chưa tái hiện với NaN/Infinity, khoảng giá trị và góc null theo test hiện có. `seat_id` sai định dạng hoặc model rỗng vẫn bị backend validator từ chối; Vision chưa xác thực sớm hai trường hợp đó.
- Nhiều pose cùng seat: đã khắc phục/chưa tái hiện; source chọn theo confidence, giao bbox và tie-break ổn định, có test hình học.
- Smoothing sau thời gian không có pose: vẫn tái hiện trong test. History cũ có thể ảnh hưởng nhãn khi pose trở lại; chưa đổi hành vi vì D-03 còn OPEN.
- GUI/browser E2E trong snapshot ban đầu: BLOCKED. Ngày 2026-11-18 đã chạy bằng Playwright trên Edge headless với API/camera mock. Một lượt chẩn đoán tìm thấy lỗi caption history sau phục hồi; lỗi đã sửa và E2E cuối cùng **6/6 PASS**. Xem addendum và [báo cáo UI](../e2e_web_playwright/report.md). ESP32-CAM, stream thật, model YOLO và bounds ghế được chủ dự án xác nhận vẫn chưa kiểm chứng.

## Addendum — chạy lại MQTT/PostgreSQL integration (2026-11-18)

Người dùng chạy lại trên Windows PowerShell sau khi Docker daemon hoạt động (`docker info --format '{{.ServerVersion}}'` trả `29.9.2`). Các biến test trỏ đến stack Compose riêng `posture-test`; không dùng stack chính hoặc `.env`.

| Ca | Input / lệnh | Output mong đợi | Output thực tế | Kết quả / ghi chú |
|---|---|---|---|---|
| INT-DB-MQTT | `py -m pytest -q -m integration tests/integration/test_mqtt_pipeline.py tests/integration/test_mqtt_recovery.py`; PostgreSQL test trên cổng 15432, broker test không xác thực trên 11883. | Pipeline MQTT → subscriber → PostgreSQL xử lý event hợp lệ, trùng và sai; subscriber nối lại sau restart broker. | `2 passed in 11.15s`. | PASS. Transcript không có test name/subcase chi tiết do `-q`; không ghi thêm số event hoặc trạng thái từng assertion ngoài nội dung test. |
| INT-MQTT-AUTH | `RUN_MQTT_AUTH_INTEGRATION=1; py -m pytest -q -m integration tests/integration/test_mqtt_auth.py`; fixture tự sinh credentials và dùng Compose project riêng. | Credential hợp lệ được chấp nhận; kết nối sai/anonymous bị từ chối; subscriber và publisher giữ hành vi theo test auth; ca persistence hoàn tất. | Dòng quan sát: `C2 rejected subscriber reconnect attempts in 30 seconds: 5`; tổng `2 passed in 287.48s (0:04:47)`. | PASS. Năm lần thử lại khi xác thực thất bại là kết quả C2 được test ghi nhận. Lệnh `-q` không hiển thị số event của từng P1–P5 trong transcript, nên không cập nhật lại số liệu từng ca durability từ lần chạy này. |
| WEB-DASHBOARD | Playwright mở Dashboard; event, API và camera là mock localhost; ca gồm nhãn/freshness, lọc/phân trang, HTTP 400/502/khôi phục, payload HTML, preview và polling. | Sau khi API trả 200 trở lại, dashboard xóa lỗi history nếu snapshot được khôi phục, kể cả danh sách event không đổi; lỗi khoảng thời gian nhập sai vẫn hiển thị khi polling bình thường. | `py -m pytest -m e2e tests/e2e_web -q`: `6 passed in 46.60s`; 10 ảnh trong thư mục screenshot. Polling đo `10.005s`, 10 request (5 mỗi endpoint). | PASS. Caption history được làm mới khi snapshot đổi hoặc lỗi history vừa phục hồi; E2E đồng thời giữ kiểm tra bộ lọc thời gian. Đây là Edge headless với mock localhost, không phải camera thật. Chi tiết tại [ma trận UI](../e2e_web_playwright/case_matrix.md). |
| FAST-SUITE | `py -m pytest -q`; bộ test nhanh theo `pytest.ini`. | Không còn assertion fail sau khi sửa test phân lớp và test HTTP availability. | `191 passed, 3 skipped, 13 deselected`; test mục tiêu backend/web `16 passed`. | PASS. 3 skipped và 13 deselected được giữ nguyên theo cấu hình/test dependency; đây không phải kết quả broker/PostgreSQL ở dòng INT phía trên. |

### Trạng thái cleanup

- Fixture auth tự dọn Compose project và volume tạm của lượt auth khi kết thúc bình thường; test kết thúc với exit code 0.
- Transcript chưa có kết quả `docker compose ... down` cho project không xác thực `posture-test`, cũng chưa xác nhận đã xóa các biến `TEST_DATABASE_URL`, `TEST_MQTT_HOST`, `TEST_MQTT_PORT` khỏi PowerShell. Cleanup hai mục này chưa được xác minh trong báo cáo.

Prompt audit tổng thể hiện có tại [`docs/agent/PROMPT_E2E_SYSTEM_SCENARIOS.md`](../../docs/agent/PROMPT_E2E_SYSTEM_SCENARIOS.md). Bộ kiểm thử giao diện đã có tại [`tests/e2e_web/test_dashboard_e2e.py`](../../tests/e2e_web/test_dashboard_e2e.py); không tạo bản E2E trùng lặp.

### Finding E2E Dashboard đã khắc phục

**Lỗi ban đầu:** với 4 event history giả lập, proxy trả 502 rồi history trả lại HTTP 200 cùng snapshot cũ; caption vẫn báo lỗi. Nguyên nhân là caption chỉ cập nhật khi snapshot đổi.

**Sửa đổi:** tách cập nhật caption history khỏi render DOM. Khi response thành công, caption được làm mới nếu snapshot đổi hoặc request trước đó lỗi; điều này cũng tránh xóa thông báo bộ lọc không hợp lệ trong các lần polling thành công bình thường. Assertion E2E kiểm tra caption sạch lỗi và đủ 4 dòng được giữ lại.

**Kết quả:** ca phục hồi riêng `1 passed in 12.07s`; cặp ca lọc + phục hồi `2 passed in 15.67s`; toàn bộ E2E `6 passed in 46.60s`. Test web liên quan `11 passed in 1.09s`; bộ test nhanh `191 passed, 3 skipped, 13 deselected in 12.11s`. Trong lượt xác minh đầu, cập nhật caption ở mọi polling làm mất cảnh báo khoảng thời gian không hợp lệ; logic đã được giới hạn và toàn bộ E2E cuối cùng qua.

### Đối chiếu với finding durability cũ

Kết quả tổng `2 passed` của module auth cho biết assertion của test lifecycle qua; transcript không in số liệu P2. Finding trước đó về hard kill trước autosave (`0/5` event được lưu trong một lượt đo ngày 2026-11-17) vẫn được giữ như số đo lịch sử, không kết luận đã khắc phục chỉ từ lượt chạy này. D-10 vẫn OPEN; không thay đổi cấu hình broker chính.

## Addendum — rà soát và chạy lại E2E (2026-11-18)

Lượt này chạy lại các test phần mềm và tích hợp trong project test riêng; không sửa mã ứng dụng hoặc hợp đồng. Working tree ban đầu đã có nhiều thay đổi chưa commit; chúng được giữ nguyên. Ba fixture integration được chỉnh để dùng `seat_id` tiền tố `TEST-`, đúng quy tắc dữ liệu audit.

| Ca | Input/điều kiện | Output mong đợi | Output thực tế | Kết quả và lý do |
|---|---|---|---|---|
| AUDIT-SOFTWARE-E2E | Event tổng hợp `TEST-S01` tạo bằng Vision event builder; backend ingest/API và web proxy chạy localhost; storage in-memory. | Event hợp lệ đi qua các lớp phần mềm, API/proxy trả đúng dữ liệu; không cần broker/DB thật. | `py -m pytest -m integration tests/integration/test_software_e2e_audit.py -q` → `1 passed in 0.85s`. | PASS. Đây là tích hợp phần mềm với HTTP server cục bộ và storage giả, không đại diện kiểm thử phần cứng hoặc dịch vụ thật. |
| AUDIT-MQTT-POSTGRES | Compose project `posture-test`; PostgreSQL test trên loopback `15432`, Mosquitto test trên loopback `11883`; dữ liệu giả `TEST-*`. | Event hợp lệ được ghi và truy vấn; event trùng/không hợp lệ không tạo bản ghi sai; subscriber tiếp tục sau broker restart. | `py -m pytest -q -m integration tests/integration/test_mqtt_pipeline.py tests/integration/test_mqtt_recovery.py` → `2 passed in 11.66s`. Compose healthcheck báo cả hai service `Healthy`. | PASS cho broker và DB test cô lập trong lần chạy này. Không dùng broker, DB hoặc stack sản phẩm. |
| AUDIT-DASHBOARD-E2E | Playwright điều khiển Edge; API/camera mock localhost; 6 kịch bản UI, gồm lọc, 400/502/khôi phục, input HTML, preview và polling. | Mỗi assertion UI qua; caption history xóa 502 khi endpoint phục hồi dù snapshot không đổi; không render payload HTML thành markup. | `py -m pytest -m e2e tests/e2e_web -q` → `6 passed in 46.34s`; 10 ảnh browser; polling `10.012s`, 10 request (5 mỗi endpoint). | PASS bằng browser automation headless. Không có công cụ desktop tương tác trong phiên nên không tuyên bố đã thao tác màn hình vật lý. Ảnh là screenshot thật từ trình duyệt test. |
| AUDIT-FAST-SUITE | Bộ test nhanh theo `pytest.ini`. | Không có test assertion fail; test tích hợp/E2E không bị tính vào lượt nhanh mặc định. | `py -m pytest -q` → `191 passed, 3 skipped, 13 deselected in 11.77s`. | PASS. 3 skipped và 13 deselected giữ nguyên theo marker/điều kiện test; không tính chúng là PASS. |
| AUDIT-HARDWARE | ESP32-CAM, stream thật, model YOLO và môi trường lớp học. | Cần có thiết bị/stream/model thật được cấp phép và quan sát được. | Không có thiết bị/stream phần cứng được nối trong môi trường test; chỉ có camera fixture tổng hợp. | BLOCKED/chưa kiểm chứng. Không suy diễn từ mock rằng firmware, stream thật, inference thật hoặc độ chính xác tư thế hoạt động. |

### Hạn chế môi trường và trạng thái test service

- Lần chạy E2E đầu không có quyền mở tiến trình Playwright Node (`WinError 5: Access is denied`). Lệnh được chạy lại với quyền thực thi browser cần thiết và qua 6/6; lần đầu là lỗi quyền môi trường, không phải lỗi assertion sản phẩm.
- Docker API ban đầu bị sandbox từ chối named pipe. Sau khi được cấp quyền chỉ cho thao tác test, `docker info` trả phiên bản `29.9.2`; compose riêng khởi động healthy. Sau test, `docker compose ... stop` dừng cả hai service; container và dữ liệu test được giữ lại, không chạy `down` hoặc xóa volume.
- Test MQTT auth không chạy lại trong addendum này. Kết quả lịch sử do người dùng cung cấp vẫn được giữ riêng ở phần trên, không cộng vào thống kê lượt hiện tại.
- ESP32-CAM, MJPEG thật, YOLO runtime/checkpoint thật, hiệu năng FPS/latency và ảnh lớp học không được kiểm chứng. D-10 về QoS/durability vẫn OPEN; kết quả hard-kill cũ là finding lịch sử, không được xác nhận lại ở lượt này.

Ảnh và log Dashboard mới nhất nằm tại [`../e2e_web_playwright/`](../e2e_web_playwright/); ma trận input/expected/actual ở [`case_matrix.md`](../e2e_web_playwright/case_matrix.md), test trình duyệt ở [`../../tests/e2e_web/test_dashboard_e2e.py`](../../tests/e2e_web/test_dashboard_e2e.py). Ảnh ghi lại Dashboard qua browser headless, không phải thao tác bằng desktop vật lý.

### Bàn giao lượt audit

- File test thay đổi: `tests/integration/test_software_e2e_audit.py`, `tests/integration/test_mqtt_pipeline.py`, `tests/integration/test_mqtt_recovery.py` — chỉ đổi seat fixture sang `TEST-*`.
- Báo cáo cập nhật: `reports/e2e_full/report.md`, `reports/e2e_web_playwright/case_matrix.md`; report browser được sinh lại bởi pytest.
- Ảnh hưởng hợp đồng chung: **Không**.
- Rủi ro còn lại: kiểm thử phần cứng/model thật cần phiên có thiết bị và stream được xác nhận; không kết luận durability từ lần chạy pipeline/recovery thông thường.
