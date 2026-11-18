# Ma trận E2E giao diện Dashboard

Ngày chạy: 2026-11-18 (giờ địa phương Asia/Bangkok).  
Lệnh: `py -m pytest -m e2e tests/e2e_web -q`  
Kết quả mới nhất sau sửa lỗi: `6 passed in 46.34s` (Edge headless, Playwright).
Dữ liệu: event tổng hợp, `seat_id` dùng tiền tố `TEST-`; API và camera chạy mock localhost.

## Input, output mong đợi và output thực tế

| ID / ca | Input và thao tác | Output mong đợi | Output thực tế | Lý do / trạng thái | Bằng chứng |
| --- | --- | --- | --- | --- | --- |
| WEB-01 `test_empty_dashboard_four_labels_and_w1_freshness` | Khởi tạo API rỗng; lần lượt gửi 4 event `upright`, `slouching`, `leaning`, `unknown`; sau đó đặt event `slouching` cũ hơn ngưỡng stale 12 giây. | Trạng thái rỗng hiển thị; 4 ghế hiện đúng nhãn; event stale không được tính là tư thế hiện tại. | Assertion đạt: 4 thẻ ghế/4 nhãn được render; stale state được đánh dấu; bộ đếm `slouching` về `0`. | PASS. UI cập nhật qua polling; stale event bị loại khỏi số liệu hiện tại theo hành vi đang kiểm tra. | `screenshots/empty-dashboard.png`, `four-labels-fresh.png`, `freshness-stale.png` |
| WEB-02 `test_filters_timezone_reverse_range_and_eight_row_pagination` | Seed 12 event giả; chuyển trang; lọc `TEST-S03` theo khoảng `2026-10-02T00:05`–`00:20`; tiếp đó nhập khoảng đảo ngược `00:30`–`00:10`. | Mỗi trang tối đa 8 dòng; bộ lọc gửi đủ query; khoảng thời gian đảo được báo không hợp lệ và không thay danh sách đã hiển thị. | Assertion đạt: trang 1 có 8 dòng, trang 2 có 4; bộ lọc trả đúng 1 dòng `TEST-S03` và query keys `from, limit, seat_id, to`; khoảng đảo hiện lỗi và giữ dòng cũ. | PASS. Kết quả khớp với pagination/filter hiện có và validation phía giao diện. | `screenshots/filter-reversed-range.png` |
| WEB-03 `test_http_400_proxy_502_and_recovery` | API history trả HTTP 400; sau đó dừng backend mock để proxy trả 502; khởi động backend và trả lại cùng 4 event. | Giữ 4 event qua lỗi; khi API phục hồi, UI Online và caption history xóa HTTP 502, báo snapshot đã tải thành công. | 4 event được giữ, API chuyển Offline rồi Online; sau response 200, caption trở lại `Hiển thị 4 / 4 sự kiện gần đây đã tải`; đủ 4 dòng vẫn hiển thị. | PASS. Caption được cập nhật khi history vừa phục hồi dù snapshot không đổi. | `screenshots/api-http-400-preserved.png`, `api-proxy-502.png`, `api-recovered.png` |
| WEB-04 `test_html_payload_is_text_and_never_creates_elements_or_runs_script` | Gửi `seat_id` tổng hợp chứa chuỗi `<img ... onerror=...>`. | Chuỗi được hiển thị như text; không tạo phần tử ảnh và không chạy script. | Assertion đạt: payload xuất hiện dạng text; số ảnh chèn trong map/history là `0`; `window.__e2eXss` không được tạo. | PASS. Kiểm tra an toàn render trên dashboard với dữ liệu API không tin cậy. | `screenshots/html-payload-safe.png` |
| WEB-05 `test_camera_url_validation_preview_stop_timeout_and_no_api_upload` | Nhập URL `javascript:`, URL có user/password, URL IPv6 lỗi; mở preview bằng server SVG giả; dừng preview; thử endpoint chậm. | URL sai bị từ chối; URL hợp lệ bật/tắt preview; timeout được báo; frame camera không được gửi lên API. | Assertion đạt: URL sai không gán `src`; preview bắt đầu/dừng đúng; endpoint chậm hiện timeout; request API chỉ là GET và không có body. | PASS có giới hạn. Camera là server SVG giả, không mô phỏng đầy đủ MJPEG/ESP32. `GET /slow` bị hủy sau timeout là hành vi dự kiến. | `screenshots/camera-timeout-no-api-upload.png` |
| WEB-06 `test_polling_request_count_over_a_defined_ten_second_window` | Mở dashboard, đợi phản hồi ban đầu, ghi request API trong cửa sổ 10 giây bằng đồng hồ monotonic. | Trong cửa sổ 10 giây có 8–12 request `/api/`, tương ứng polling hai endpoint xấp xỉ mỗi 2 giây. | Đo được `10.012s`, tổng `10` request: `/api/events` = `5`, `/api/events/latest` = `5`. | PASS. Đo xác nhận hai endpoint được polling riêng; không tính request khởi tạo ngoài cửa sổ. | `polling_measurement.json`, `screenshots/polling-ten-second-window.png` |

## Quan sát lỗi trình duyệt

- Không ghi nhận `pageerror` JavaScript trong log Playwright.
- Các phản hồi HTTP 400/404/502 được kích hoạt có chủ ý trong ca lỗi; chúng là trạng thái đầu vào của test, không phải lỗi ngoài dự kiến.
- Request `GET /slow` bị `net::ERR_ABORTED` khi giao diện hủy preview sau timeout; đây là kết quả kỳ vọng của ca timeout.
- `browser_logs.jsonl` được mở ở chế độ append nên chứa nhiều hơn một lượt chạy; không dùng tổng số log của file để đếm số lỗi cho riêng lượt ngày 2026-11-18.

## Giới hạn phạm vi

Đây là E2E lớp giao diện với API/camera giả. Nó không xác minh luồng thật ESP32-CAM → YOLO → MQTT → PostgreSQL → dashboard, cũng không đo độ chính xác tư thế hay FPS. Kiểm thử broker/PostgreSQL thật được người dùng chạy riêng ngày 2026-11-18 và ghi trong [`../e2e_full/report.md`](../e2e_full/report.md). ESP32-CAM, stream thật và model YOLO vẫn chưa kiểm chứng.

## Kiểm tra rộng hơn trong cùng lượt

Bảng dưới là kết quả tại thời điểm audit ban đầu, trước khi xử lý ba test fail. Kết quả xác minh sau xử lý được ghi riêng ở mục “Tái kiểm tra”.

| Lệnh | Output mong đợi | Output thực tế | Đánh giá / lý do |
| --- | --- | --- | --- |
| `py -m pytest -q` | Bộ test nhanh theo `pytest.ini` chạy hết; test DB/broker được skip nếu thiếu dịch vụ; không có assertion lỗi. | `187 passed, 3 skipped, 13 deselected`; 3 failed: `test_every_backend_module_belongs_to_a_known_layer`, `test_layers_only_import_downwards`, `test_dashboard_keeps_endpoint_snapshots_independent_and_marks_http_replies_reachable`. | FAIL. Hai lỗi backend do `backend/tools/benchmark_backend.py` chưa được ánh xạ vào layer trong bảng kiến trúc test. Lỗi web kỳ vọng chuỗi gọi `DashboardUtils.hasHttpResponse(responses)` đã cũ so với mã `app.js` hiện tại; các assertion E2E trình duyệt về Online/Offline và phục hồi vẫn qua. Cần cập nhật test kiến trúc/contract test hoặc làm rõ phân lớp trước khi coi CI xanh. Không sửa các module trong lượt audit này. |
| `py -m pytest -q -m integration tests/integration/test_software_e2e_audit.py` | Một event tổng hợp đi qua Vision event builder → backend ingest/API → web proxy; dedup/API response đúng. | `1 passed in 2.25s`. | PASS cho tích hợp phần mềm dùng in-memory store và các HTTP server cục bộ; không dùng broker/PostgreSQL thật. |
| Docker daemon probe `docker info --format '{{.ServerVersion}}'` | Docker daemon khả dụng để chạy broker/PostgreSQL test riêng. | `permission denied` khi kết nối named pipe `dockerDesktopLinuxEngine`. | BLOCKED. Broker/PostgreSQL integration và recovery không được chạy lại; không khởi động compose chính. |

## Findings cần xử lý

1. **Test nhanh ban đầu có ba lỗi đã được xử lý:** hai lỗi architecture do `tools` chưa được phân loại; lỗi web do assertion kiểm tra source string cũ. Kết quả sau xử lý ở mục “Tái kiểm tra”.
2. **Vision reconnect callback và trạng thái theo ghế:** tài liệu audit trước đó ghi nhận callback Paho API version không khớp chữ ký, smoothing theo ghế chưa reset khi rời ghế, và khả năng nhiều pose cùng tạo event một `seat_id`. Những điểm này không được tái kiểm chứng qua broker/stream thật trong lượt hiện tại; xem [audit findings và prompt theo module](../../docs/agent/AUDIT_FINDINGS_AND_FOLLOWUP_PROMPTS.md), coi là finding cần xác minh lại chứ không phải kết quả của lần chạy hôm nay.
3. **Phân biệt ghế trống với pipeline dừng:** dashboard chỉ có event/tuổi event từ API hiện hành; không có heartbeat trạng thái theo hợp đồng hiện tại. Không kết luận được camera/Vision offline chỉ từ giao diện. D-04 vẫn cần nhóm chốt; không tự đổi hợp đồng.
4. **Đã sửa lỗi hook tạo báo cáo sai:** chạy test thường từng bị hook hiểu nhầm `not e2e` là lượt E2E và ghi đè report thành BLOCKED. Hook hiện kiểm tra marker trên danh sách test đã thu thập; lượt pytest thường không ghi đè kết quả. Report E2E mới nhất đang ghi FAIL cho finding phục hồi history bên dưới.

## Tái kiểm tra sau khi xử lý ba test fail

Ngày 2026-11-18, sau khi cập nhật quy tắc phân lớp và chuyển test web sang kiểm tra hành vi:

- `py -m pytest -q tests/test_backend_architecture.py tests/test_web_accessibility.py tests/test_web_dashboard_utils.py` → **16 passed**.
- `py -m pytest -q` → **191 passed, 3 skipped, 13 deselected**; không còn test fail.
- `py -m pytest -m e2e tests/e2e_web -q` → **6 passed in 61.50s** trên Edge headless.

Hai file backend tool được giữ tại `backend/tools/` như điểm vào ngoài runtime; tool được phép import `config`, `infrastructure`, `repositories`, còn test layer runtime tiếp tục cấm import ngược từ `tools`. Test web hiện kiểm tra `hasAvailableEndpoint`: HTTP 4xx là phản hồi từ server, 5xx hoặc lỗi mạng không được tính là endpoint khả dụng. E2E xác nhận luồng 400/502 và phục hồi.

## Kết quả E2E UI sau khi sửa finding

- Lệnh: `py -m pytest -m e2e tests/e2e_web -q`.
- Output: **6 passed in 46.60s**. Ca `test_http_400_proxy_502_and_recovery` xác nhận caption lỗi được xóa khi history trả HTTP 200 dù snapshot không đổi.
- Trong một lượt E2E trung gian, cập nhật caption ở mọi polling thành công đã làm thông báo khoảng thời gian không hợp lệ biến mất. Đã giới hạn cập nhật caption khi snapshot đổi, người dùng chuyển trang, hoặc history vừa phục hồi từ lỗi; cả ca lọc thời gian lẫn ca phục hồi đều qua sau chỉnh sửa này.
- 10 file ảnh hiện có; ảnh `api-recovered.png` được tạo mới ở lượt xanh và cho thấy Online, đủ 4 event lịch sử, caption đã tải thành công. Không có `pageerror` JavaScript trong log.
- E2E kiểm thử giao diện không chạy trên màn hình vật lý: Playwright điều khiển Edge headless và lưu screenshot; các screenshot được xem để kiểm tra render.

### Kiểm thử bổ sung

- Ca phục hồi riêng: `1 passed in 12.07s`.
- Ca lọc thời gian và phục hồi chạy cùng: `2 passed in 15.67s`.
- Test web liên quan: `11 passed in 1.09s`.
- Bộ test nhanh: `191 passed, 3 skipped, 13 deselected in 12.11s`.

Finding caption history sau phục hồi đã được sửa trong `web/app.js`; assertion E2E được giữ lại làm regression test.

Prompt audit tổng thể đã có tại [`docs/agent/PROMPT_E2E_SYSTEM_SCENARIOS.md`](../../docs/agent/PROMPT_E2E_SYSTEM_SCENARIOS.md). File E2E Playwright [`tests/e2e_web/test_dashboard_e2e.py`](../../tests/e2e_web/test_dashboard_e2e.py) đã có sẵn; trong lượt này được bổ sung assertion kiểm tra lỗi history sau phục hồi, không tạo suite trùng lặp.
