# Báo cáo kiểm thử E2E Backend và Web

## 1. Tóm tắt

- Ngày: 2026-11-16 (Asia/Bangkok).
- Môi trường: workspace Windows/PowerShell theo IDE context. Trình duyệt và phiên bản dịch vụ: chưa quan sát được.
- Phạm vi đã làm: khám phá tĩnh mã nguồn/tài liệu. Không khởi động service, không publish dữ liệu, không gửi API request, không thao tác trình duyệt và không truy vấn DB.
- Số ca trong báo cáo: 1 khám phá tĩnh (PASS); 8 nhóm xác minh động (BLOCKED). Không có FAIL được quan sát; điều này không khẳng định hệ thống chạy đúng.
- Đánh giá chung: **chưa đủ bằng chứng để đánh giá vận hành**. Phiên này không có công cụ điều khiển trình duyệt/màn hình hoặc chụp ảnh; do đó không thể đáp ứng điều kiện quan sát và lưu screenshot cho các ca API/UI.
- Thư mục `screenshots/` được tạo nhưng hiện không có ảnh. Không tạo ảnh minh họa giả.

## 2. Khám phá hợp đồng và tính năng (DISC-01 — PASS, chỉ kiểm tra tĩnh)

Nguồn đã đọc: `backend/README.md`, `web/README.md`, `backend/config.py`, `backend/domain/contract.py`, `backend/domain/validator.py`, `backend/interfaces/http_api.py`, `backend/infrastructure/migrations.py`, `backend/migrations/001_create_posture_events.sql`, `backend/repositories/event_repository.py`, `web/app_web.py`, `web/app.js`, `docker-compose.test.yml`, `docs/agent/DATA_CONTRACT.md`.

- MQTT topic mặc định: `classroom/posture/events` (`backend/config.py:12`).
- Payload bắt buộc theo validator: `event_id`, `ts`, `seat_id`, `label`, `confidence`, `model`, `angles`; nhãn `upright`, `slouching`, `leaning`, `unknown`; giới hạn payload 16,384 byte (`backend/domain/contract.py:3-11`).
- DB: bảng `posture_events`, khóa duy nhất `event_id`, nhãn và confidence có CHECK constraint; index theo `ts` và `(seat_id, ts)` (`backend/migrations/001_create_posture_events.sql:1-12`). Chưa xác minh migration thực sự đã áp trong DB.
- Endpoint thấy trong router: `GET /api/events/latest`, `GET /api/events`; trả JSON (`backend/interfaces/http_api.py:33-43`). README nêu query `from`, `to`, `seat_id`, `limit` mặc định 100/tối đa 500, dữ liệu trả gồm `event_id`, `ts`, `seat_id`, `label`, `trunk_angle`, `confidence`, `model_version` (`backend/README.md:31-34`). Không thấy `offset`/phân trang server-side.
- Validator source hiện từ chối `confidence` kiểu bool và giá trị không hữu hạn (`backend/domain/validator.py:40-46`); góc được giới hạn theo miền REAL PostgreSQL (`:59-62`). Đây chưa phải kiểm thử runtime.
- Dashboard source gọi hai endpoint trên, gửi `limit=100`, phân trang cục bộ 8 dòng và polling 2 giây (`web/app.js:103-136, 153-156, 294`). README xác nhận lịch sử chỉ tải tối đa 100 event và backend chưa có offset/page (`web/README.md:23`).
- `web/app_web.py` phục vụ static, proxy GET `/api/`, trả 404 cho đường dẫn không hợp lệ và 502 khi backend không sẵn sàng theo nhánh xử lý source (`web/app_web.py:28-42, 61-75, 95-110`). Chưa kiểm tra runtime.
- Không tìm thấy route OpenAPI/Swagger, `has_skeleton`, endpoint skeleton, CSV export, hoặc purge keypoints trong các file được rà soát. Tạm ghi **chưa thấy trong source**; không kết luận N/A/thiếu OpenAPI bằng trình duyệt vì chưa thể mở các URL được yêu cầu.
- README backend hướng dẫn Docker Compose và `web/app_web.py`, không thấy hướng dẫn Nginx tại `backend/README.md`/`web/README.md`. README gốc chỉ có Quick Start tổng quan, không có lệnh chạy web cũ để đối chiếu. Chưa chạy lệnh nào nên chưa kết luận lệnh nào chạy được.
- Test compose khai báo PostgreSQL 16 và Mosquitto 2.0, cổng loopback 15432/11883, không khai báo volume (`docker-compose.test.yml:1-25`). Chưa khởi động nên chưa xác minh phiên bản thực tế/healthcheck.

## 3. Kết quả theo nhóm

Quy ước: vì không có thao tác trình duyệt hay ảnh chụp màn hình trong phiên, các kiểm tra đòi hỏi UI/API qua giao diện được đánh dấu BLOCKED. Output mong đợi chỉ dựa trên nguồn code/tài liệu ghi kèm, không sửa theo kết quả. Output thực tế là trạng thái thực sự quan sát được: bước kiểm thử chưa chạy. Không có status/body/header runtime để trích dẫn.

| ID | Mô tả | Cách thực hiện | INPUT | OUTPUT MONG ĐỢI (nguồn) | OUTPUT THỰC TẾ | Kết quả | Ghi chú |
|---|---|---|---|---|---|---|---|
| DISC-01 | Khám phá endpoint/topic/schema và feature | Đọc source/docs | Các file liệt kê tại mục 2 | Router có 2 GET; topic/payload/schema theo source | Đã thấy các khai báo được liệt kê mục 2 | PASS (tĩnh) | Không phải xác minh runtime |
| INFRA-01 | Khởi động test DB/broker, healthcheck, migration | Terminal theo `backend/README.md` | `docker compose -p posture-test -f docker-compose.test.yml up -d --wait` | Compose khởi động PostgreSQL/Mosquitto và chờ healthcheck; nguồn `backend/README.md` mục Tests, `docker-compose.test.yml:1-25` | Chưa chạy; không có log/phiên bản thực tế | BLOCKED | Không có quan sát service trong phiên |
| MQTT-01 | Luồng hợp lệ/trùng/không hợp lệ và khôi phục broker/DB | Terminal publish + đối chiếu subscriber/DB | Payload giả với `TEST-*`; ca lỗi theo đề bài | Hợp lệ lưu một lần; trùng không nhân bản; sai bị từ chối theo validator/DB constraints | Chưa publish; không có log hoặc DB output | BLOCKED | Không tạo dữ liệu thử nên không cần cleanup |
| API-01 | Swagger/OpenAPI discovery | Mở `/docs`, `/openapi.json`, `/swagger`, `/redoc` trên trình duyệt | Các URL trên | Nếu có Swagger thì UI/OpenAPI hiển thị; nếu không phải ghi nhận từ màn hình | Chưa mở được URL; không có status/body/header hoặc screenshot | BLOCKED | Không kết luận phát hiện P3 thiếu OpenAPI |
| API-02 | `GET /api/events/latest` và `GET /api/events` trên Swagger | GUI: Try it out/Execute | Query rỗng, lọc `seat_id`, thời gian, limit; dữ liệu test | JSON đúng schema theo `backend/README.md:31-34`; limit mặc định 100, tối đa 500 | Chưa gửi request; không có response quan sát | BLOCKED | Chưa kiểm tra success/empty/error/latency |
| API-03 | Tham số sai, method/path sai, bool confidence/góc NaN/Infinity qua ingest | GUI cho API; publish terminal cho MQTT | ID sai, thời gian sai, limit sai; payload invalid | Lỗi được từ chối/HTTP 4xx theo handler; validator từ chối bool/nonfinite theo `backend/domain/validator.py:40-46` | Chưa thực thi; không có status/body | BLOCKED | Source inspection không thay cho runtime test |
| WEB-01 | Dashboard, console, network, file tĩnh/proxy | Trình duyệt GUI + DevTools | Mở `http://localhost:8080`, quan sát Console/Network | Static tải; hai `/api` GET thành công; polling 2 giây theo `web/app.js:153-156,294` | Không mở trình duyệt; không có chữ UI/console/network/screenshot | BLOCKED | Không khởi động service |
| WEB-02 | Bộ lọc, trang, empty/error state, responsive, dữ liệu bất thường | Thao tác chuột/bàn phím và DevTools | Ghế/thời gian test, resize, backend tắt/bật | Hành vi cần quan sát trực tiếp; phân trang cục bộ 8 dòng theo source | Chưa thao tác; không có output UI | BLOCKED | Không xác minh XSS/layout/hồi phục |
| WEB-03 | Skeleton/CSV/purge keypoints nếu tồn tại | GUI + kiểm tra artifact | Chọn event/export/purge | Chỉ kỳ vọng nếu feature có triển khai | Chưa thao tác; rà soát source mục 2 chưa thấy các feature này | BLOCKED | Chưa gắn N/A runtime; chưa tìm thấy trong source đã rà |
| E2E-01 | Publish → subscriber → DB → API → dashboard và đo latency | Terminal + GUI | Chuỗi event `TEST-*`, ghế trống và đổi nhãn | Mỗi chặng phản ánh cùng event; latency đo từ thời điểm publish đến UI | Chưa publish/đối chiếu; không có số đo | BLOCKED | Không đưa ra số đo ước tính |

## 4. Danh sách lỗi

- Chưa ghi nhận lỗi vận hành vì không chạy được ca runtime.
- Chưa mở trình duyệt để xác nhận Swagger thiếu; không tạo finding P3 này chỉ từ việc không thấy router OpenAPI trong source đã rà.
- Khả năng kiểm tra confidence bool và giá trị không hữu hạn đã có trong source (`backend/domain/validator.py:40-46`), nhưng chưa xác nhận bằng publish/runtime.

## 5. Chưa xác minh

- Toàn bộ trạng thái service, phiên bản thực tế, migration/index trong DB, healthcheck, reconnect/loss message.
- Mọi response/status/header API và thao tác Swagger.
- Dashboard, Console/Network, bộ lọc/trang, tải CSV, responsive, lỗi backend và phục hồi.
- Các tính năng keypoints/skeleton/purge và E2E latency.
- Tất cả kết quả runtime; không có Docker/browser evidence trong báo cáo.
- Dù test động sau này thành công, phạm vi vẫn chỉ là dữ liệu giả mỗi ghế một người; chưa kiểm chứng trong lớp học thật nhiều người.

Lý do chặn: phiên công cụ hiện có không cung cấp điều khiển máy tính/trình duyệt hoặc chụp màn hình. Các yêu cầu bắt buộc cần đọc response/UI ngay trên màn hình và lưu ảnh không thể thay bằng gọi API qua script.

## 6. Dọn dẹp

- Không khởi động service, không tạo/publish dữ liệu, không chạy purge; vì vậy không có dữ liệu test để xóa và không có service do lượt này khởi động cần dừng.
- Không sửa code nguồn, không tạo nhánh, không commit/push. Chỉ tạo báo cáo và thư mục `screenshots/` theo yêu cầu.
- Không đọc/in nội dung `.env`; không ghi khóa/mật khẩu vào báo cáo.

## 7. Đề xuất theo ưu tiên

1. Chạy lại phần API/Web trên phiên có trình duyệt điều khiển và screenshot thật; dùng test DB/broker riêng theo README.
2. Sau khi có thể chạy test stack, thực hiện MQTT/DB/API và cleanup dữ liệu `TEST-*`, lưu lệnh, log và response quan sát được.
3. Xác nhận qua trình duyệt các nhánh error/empty/responsive và feature skeleton/CSV; chỉ đánh N/A sau khi xác minh không triển khai.
4. Ghi phiên bản dịch vụ, tổng số PASS/FAIL/BLOCKED/N/A và latency chỉ từ lần chạy có bằng chứng.

**Xác nhận:** lượt này không sửa mã nguồn, không tạo nhánh, không commit, không push và không đưa bí mật vào báo cáo. Không có ảnh chụp được tạo; các ca yêu cầu screenshot đã được đánh dấu BLOCKED.
