# Báo cáo retest E2E backend/dashboard

Ngày chạy: 2026-11-16 (UTC+07:00)  
Môi trường: Windows PowerShell; Docker Compose test riêng `posture-test`; broker `eclipse-mosquitto:2.0` chạy phiên bản 2.0.22; PostgreSQL 16 Alpine; API local `127.0.0.1:18000`; subscriber local; broker host `127.0.0.1:11883`. Broker config test đã mount read-only, có `listener 1883`, `allow_anonymous true`, `persistence false`; mapping chỉ loopback. Log không có dòng “local only mode”.  
Kết quả: **24 PASS, 7 BLOCKED, 1 N/A**. Không phát hiện lỗi chức năng backend trong các ca đã chạy. Phần dashboard GUI chưa có bằng chứng vì phiên này không cung cấp điều khiển browser/screen/chụp ảnh.

Phạm vi chỉ gồm dữ liệu tổng hợp, giả định mỗi ghế một người; không có camera hoặc lớp học thật. API và subscriber được khởi chạy trực tiếp từ module với biến môi trường test tường minh, không gọi entry point có `load_dotenv`; không mở/đọc `.env`.

## Kết quả theo ca

| ID | Cách | INPUT | OUTPUT MONG ĐỢI (nguồn) | OUTPUT THỰC TẾ | Kết quả / ghi chú |
|---|---|---|---|---|---|
| MQTT-00 | Terminal, client Paho độc lập từ host | Subscribe và publish `handshake-ok` tới topic thử `TEST-handshake/*`, broker `127.0.0.1:11883` | Client kết nối, subscribe và nhận đúng payload. `docker-compose.test.yml:17-25`, `docker/mosquitto-test.conf:1-4` | Nhận `handshake-ok`; client không bị ngắt trước khi nhận. Broker log Mosquitto 2.0.22, mở listener IPv4/IPv6 1883; không có log local-only. | PASS; trạng thái trước FAIL → PASS. |
| MQTT-01-B1 | Terminal: publish MQTT → DB → HTTP API | Bốn label `upright/slouching/leaning/unknown`, bốn `TEST-B1-*` | Mỗi event hợp lệ được lưu 1 dòng; latest/history có thể truy vấn. `contract.py:3-6`, `validator.py:13-64`, `mqtt_consumer.py:37-78`, `event_repository.py:31-86` | DB counts `[1,1,1,1]`; GET latest `200`, có TEST-B1 seat; GET history filter `200`, 1 dòng. | PASS |
| MQTT-01-B2 | Terminal | Publish cùng UUID hai lần, seat `TEST-B2-dup` | Một dòng, log duplicate ignored. `event_repository.py:31-46`, `mqtt_consumer.py:52-78` | Count trước/sau `[1,1]`; log `[mqtt] duplicate event ignored`. | PASS |
| MQTT-01-B3 | Terminal | `unknown` + null angles; confidence 0/1; seat lengths 1/32; non-unknown + null | unknown/null và giá trị biên hợp lệ được chấp nhận; non-unknown/null bị loại. `validator.py:25-64` | Các dòng kiểm tra hợp lệ có counts `[1,1]`; non-unknown/null count `0`. | **BLOCKED một phần:** harness đã dùng seat `T` cho trường hợp 1 ký tự, trái quy tắc mọi dữ liệu phải có tiền tố `TEST-`; UUID tương ứng đã được xóa và DB xác nhận 0 dòng còn khớp. Kết quả 1 ký tự không được tính là bằng chứng hợp lệ. 32 ký tự, unknown/null và confidence biên đã qua. Tiền tố `TEST-` dài 5 ký tự nên yêu cầu thử độ dài 1 ký tự mâu thuẫn với quy tắc dữ liệu; chưa có cách thỏa cả hai. |
| MQTT-01-B4 | Terminal | 16 payload lỗi: thiếu/thừa field, UUID sai, timestamp thiếu timezone, seat rỗng/33 ký tự, label lạ, confidence 1.5/-0.1/true/string, angle NaN/Infinity, JSON hỏng, rỗng, >16,384 bytes; wrong topic; sau đó gửi sentinel hợp lệ | Payload lỗi/wrong topic không ghi DB; subscriber còn chạy và nhận sentinel hợp lệ. `contract.py:3-6`, `validator.py:13-75`, `mqtt_consumer.py:37-78` | Cả 16 invalid có count 0; wrong topic count 0; sentinel `TEST-B4-alive` count 1. | PASS. Expected ghi trước nêu 15 biến thể; thực tế harness gửi 16 (danh sách input cụ thể ở `commands.md`). |
| MQTT-01-B5 | Terminal | 50 UUID khác nhau, 10 seat `TEST-B5-*`, timestamp tăng dần | 50 dòng DB; API trả đủ 50 theo thứ tự mới nhất trước. `event_repository.py:65-86` | DB 50; API status 200, 50 event khớp, timestamp newest-first đúng; elapsed 2.55 giây. | PASS |
| MQTT-01-B6 | Terminal | Restart broker test, chờ subscribe lại, publish `TEST-B6-recovered` | Subscriber reconnect/subscribe và lưu event sau khi broker hoạt động lại. `mqtt_consumer.py:11, 95-138` | Log `[mqtt] ready; subscribed topic=classroom/posture/events; mid=2`; event count 1; 3.63 giây đến lúc xác nhận lưu. | PASS; trạng thái trước BLOCKED → PASS. |
| MQTT-01-B7 | Terminal | Dừng PostgreSQL test, publish QoS1 event, bật DB lại, publish sentinel mới | Ghi nhận retry/ACK/recovery thật; sentinel sau phục hồi được lưu. `ingest_service.py:31-69`, `mqtt_consumer.py:37-78` | Lượt retest có log subscriber `[mqtt] event stored` hai lần sau khi DB lên; event gửi lúc DB dừng có count 1 sau phục hồi; sentinel mới count 1. Không thu được log retry/disconnect trong thời gian DB dừng. | PASS về lưu và tiếp tục hoạt động; chi tiết retry bên trong chưa quan sát được từ log. Trạng thái trước BLOCKED → PASS một phần. |
| API-06a | Terminal, URL được percent-encode | `from` muộn hơn `to` | 400 `{"error": "Invalid query parameters"}`. `query.py:24-40`, `http_api.py:44-87` | 400, `application/json; charset=utf-8`, body đúng nguyên văn. | PASS |
| API-06b | Terminal | `from < to`, UTC hợp lệ | 200, chỉ event trong khoảng | 200; các event thử nghiệm trong khoảng; URL thực tế được ghi ở `commands.md`. | PASS |
| API-06c | Terminal | Chỉ `from` | 200 | 200 JSON. | PASS |
| API-06d | Terminal | Chỉ `to` | 200 | 200 JSON. | PASS |
| API-06e | Terminal | `from == to` | 200, có thể rỗng nếu không có timestamp trùng | 200, body `[]`. | PASS |
| API-06f | Terminal | Timestamp không có timezone | 400 | 400, `{"error": "Invalid query parameters"}`. | PASS |
| API-06g | Terminal | `limit=1` + `seat_id=TEST-B1-0` | 200, tối đa 1 dòng đúng seat | 200, 1 dòng đúng seat. | PASS |
| D1 | Terminal | POST/PUT/PATCH/DELETE tới `/api/events` | 405 JSON, `Content-Type: application/json; charset=utf-8`, `Allow: GET`, body `{"error": "Method not allowed"}`. `http_api.py:61-95` | Cả bốn method đều trả status/header/body đúng. | PASS |
| D1-UNKNOWN | Terminal | POST/PUT/PATCH/DELETE tới `/api/not-a-route` | Đường dẫn được kiểm tra trước method: 404 JSON. `http_api.py:58-87` | Cả bốn trả 404, JSON `{"error": "Not found"}`, không có Allow. | PASS |
| D1-GET | Terminal | GET `/api/events/latest` | 200 JSON, endpoint đọc cũ còn hoạt động | 200, `application/json; charset=utf-8`. | PASS |
| D2 | Terminal | Stop PostgreSQL test; GET latest; start DB; GET lại | 503 JSON khoảng 2 giây và <5 giây; sau khôi phục 200. `config.py:12-14,92-100`, `database.py:15-30`, `http_api.py:26-35,76-87` | 503, body `{"error": "Service temporarily unavailable"}`, elapsed **2.008 giây**; sau start DB nhận 200. | PASS; trực tiếp xác nhận timeout cấu hình mới. |
| D3 / E1 | GUI | Dashboard mở ban đầu, Console/Network và ảnh chụp | Trang render, request API 200, ảnh thật | Không thao tác được; phiên không có công cụ browser/computer/screenshot. | BLOCKED; `screenshots/` không có ảnh. |
| E2 | GUI | Publish một event mới và đo cập nhật dashboard | Seat/label/góc/confidence/time hiển thị đúng trong một chu kỳ; không request chồng | Không thể quan sát UI/Network. | BLOCKED |
| E3 | GUI | Dừng/bật backend khi dashboard mở | Có thông báo lỗi; tự hồi phục; không request chồng | Không thể thao tác hoặc chụp màn hình. | BLOCKED |
| E4 | GUI | Seat dài/ký tự đặc biệt/HTML | Hiển thị an toàn, không thực thi script/vỡ layout | Không thể xác minh qua trình duyệt. | BLOCKED |
| E5 | GUI | Trạng thái DB rỗng | Trạng thái rỗng hợp lý | Không thể xác minh UI. | BLOCKED |
| E6 | GUI | Resize cửa sổ/device emulation | Chữ không che/tràn | Không thể dùng DevTools/GUI. | BLOCKED |
| FEATURE-01 | — | Lọc lịch sử UI, skeleton, CSV | Chỉ kiểm tra nếu đã triển khai | Theo phạm vi trước đó, các tính năng này chưa có. | N/A |

## So sánh với báo cáo trước

- MQTT-00: FAIL → PASS; broker test giờ dùng listener từ host qua loopback, độc lập đã nhận lại payload.
- MQTT-01: BLOCKED → phần lớn PASS; B1/B2/B4/B5 và phục hồi broker/DB đã đi qua MQTT → subscriber → PostgreSQL → API. B3 còn giới hạn vì quy tắc tiền tố TEST mâu thuẫn với seat một ký tự.
- API-06: ca chờ chạy lại → PASS cho các trường hợp nêu trên.
- Các sửa mới D1/D2: PASS trên server/API đang chạy.
- Dashboard: chưa đổi trạng thái xác minh vì không có điều khiển trình duyệt và không có ảnh màn hình.

## Lỗi / sai lệch / rủi ro

| ID | Mức | Tái hiện / mong đợi / thực tế | Nghi ngờ |
|---|---|---|---|
| RETEST-B3-SCOPE | P3 (chất lượng bằng chứng, không phải lỗi ứng dụng) | Test độ dài 1 ký tự cần seat `T`, nhưng quy tắc bắt buộc yêu cầu prefix `TEST-`. Harness đã gửi `T`; dòng đã xóa và không còn trong DB. Không thể xem đây là phép thử tuân thủ quy tắc. | Mâu thuẫn trong yêu cầu kiểm thử. Cần chốt ưu tiên hoặc bỏ kiểm tra độ dài 1 ký tự trong lượt chỉ dùng seat TEST-. |
| RETEST-B4-COUNT | P3 | Expected ghi 15 payload lỗi; actual là 16 (có 16 kết quả count 0). | Báo cáo expected trước chạy không khớp số trường hợp trong harness; không làm thay đổi kết quả validator. |
| RETEST-B7-LOG | P3 | Event gửi khi DB dừng được lưu sau phục hồi; không thấy log retry/disconnect trong lúc DB dừng. | Không xác định được từ log liệu subscriber đã retry hay broker giữ message QoS1 cho tới khi subscriber nhận lại. |
| RETEST-GUI | BLOCKED | Không có ảnh/trạng thái thật cho các thao tác dashboard. | Thiếu công cụ điều khiển browser/screen ở phiên này. |
| RETEST-CLEANUP-TRACE | P3 | Một lượt B7 phụ trước lượt ghi nhận UUID cuối cùng chỉ in counts; script vẫn xóa hai UUID cụ thể trong bộ nhớ và xác nhận 0 dòng nhưng không in lại UUID trong log. | Thiếu traceability cho hai ID đã dọn ở lượt phụ đó. Lượt B7 sau có log UUID đầy đủ. |

Không có lỗi backend/API mức P1/P2 được phát hiện trong các phép thử đã thực hiện. Broker startup có cảnh báo `chown: /mosquitto/config/mosquitto-test.conf: Read-only file system`, nhưng broker 2.0.22 vẫn chạy và healthcheck MQTT publish/subscribe đạt; ghi nhận P3 để rà soát nếu muốn loại bỏ cảnh báo.

## Chưa xác minh

- Không xác minh hình ảnh UI, Console, Network, DOM, responsive, trạng thái lỗi dashboard hoặc script injection do thiếu công cụ browser/screen. Không có ảnh chụp nào được tạo.
- B3 seat 1 ký tự không có bằng chứng hợp lệ theo ràng buộc tiền tố `TEST-`.
- B7 không quan sát được log retry/disconnect khi PostgreSQL thực sự đang dừng; chỉ xác nhận event trong lúc dừng đã được lưu sau phục hồi và sentinel mới lưu được.
- Kết quả chỉ áp dụng dữ liệu tổng hợp, giả định mỗi ghế một người; chưa có camera hoặc lớp học thật. Không kết luận về độ chính xác model, độ trễ camera hoặc năng lực khi triển khai thực địa.

## Dọn dẹp

- Harness chính xóa đúng 77 giá trị event_id đã tạo/đưa vào payload (trong đó `not-a-uuid` là UUID sai dùng làm input validator); output xác nhận `remaining_matching_rows: 0`.
- Các lượt B7 riêng xóa UUID cụ thể và xác nhận 0 dòng; UUID lượt B7 cuối được ghi trong `commands.md`. Một lượt phụ trước đó không in UUID, như ghi ở RETEST-CLEANUP-TRACE.
- Dừng API local và subscriber local sau harness. Stack cuối cùng được dừng bằng `docker compose -p posture-test -f docker-compose.test.yml down`, không dùng `-v`; trạng thái xác minh sau dọn ở `commands.md`.

## Đề xuất

1. Chạy lại nhóm E trên máy/phiên có trình duyệt điều khiển được và lưu ảnh cho từng ca.
2. Chốt cách giải quyết mâu thuẫn giữa seat 1 ký tự và yêu cầu tiền tố `TEST-` trước lượt kiểm tra lại B3.
3. Nếu cần bằng chứng retry DB rõ hơn, bổ sung log an toàn chỉ ghi loại lỗi/trạng thái retry, không ghi payload/DSN; chạy B7 có thu log tiến trình từ trước lúc stop DB.
4. Điều chỉnh checklist B4 để expected và số payload thực tế cùng là 16.
