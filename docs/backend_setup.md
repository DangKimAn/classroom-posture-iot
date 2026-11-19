# Hướng dẫn chạy backend và dashboard (TV3)

## Chạy toàn bộ stack bằng Docker Compose

1. Cài và khởi động Docker Desktop.
2. Từ thư mục gốc repo, tạo `.env` từ `.env.example`. Đặt `MQTT_USERNAME` và `MQTT_PASSWORD` riêng, đủ mạnh; đổi mọi giá trị mẫu trước khi dùng. Không commit `.env`.
3. Chạy `docker compose up --build`.
4. Mở dashboard tại `http://localhost:8080`.

Compose khởi động Mosquitto, PostgreSQL, API, MQTT subscriber và Nginx phục vụ web. API và subscriber là hai service riêng dùng chung image backend. Dashboard được Nginx phục vụ tại `http://localhost:8080`; Nginx proxy `/api/` sang service `api`, nên cùng origin và không cần CORS. PostgreSQL và Mosquitto lưu dữ liệu trong các named volume `posture_pgdata` và `mosquitto_data`; `docker compose down` giữ các volume. Chỉ xóa volume khi chủ ý xóa dữ liệu. Các cổng host chỉ bind loopback.

Mosquitto yêu cầu xác thực trên cả MQTT (1883) và WebSocket (9001). Khi container broker khởi động, nó tạo file mật khẩu đã băm trong volume riêng từ `MQTT_USERNAME`/`MQTT_PASSWORD`; file này không nằm trong repo. Cổng 9001 vẫn bật để giữ khả năng tương thích WebSocket. Các cổng host mặc định chỉ bind loopback. Khi demo qua LAN lớp học, sửa địa chỉ bind `127.0.0.1` trong `docker-compose.yml` thành IP LAN của máy chạy Compose (cho các cổng cần dùng), chỉ cho phép mạng lớp học qua firewall, và cấp cùng credentials cho client; không mở broker ra Internet.

Healthcheck broker chỉ subscribe, không publish: `mosquitto_sub` đọc `$SYS/broker/version` với giới hạn một message và timeout 5 giây. Tài liệu Mosquitto mô tả `$SYS/broker/version` là trạng thái tĩnh được gửi một lần cho mỗi client khi subscribe; `mosquitto_sub -C` thoát sau số message đã nhận và `-W` giới hạn thời gian chờ sau khi kết nối. Trong Compose, viết `$$SYS` để Compose chuyển thành `$SYS` cho shell. Nguồn: [Mosquitto broker status](https://mosquitto.org/man/mosquitto-8.html) và [mosquitto_sub options](https://mosquitto.org/man/mosquitto_sub-1.html). Runtime healthcheck chưa được kiểm chứng trong môi trường Docker hiện tại.

Để kiểm tra runtime sau khi cập nhật, từ repo root chạy `docker compose up -d --build mqtt-broker`, sau đó `docker compose ps mqtt-broker` và `docker inspect --format '{{.State.Health.Status}}' iot_posture_mqtt`. Lệnh đầu có thể recreate/restart broker; chỉ chạy khi thời điểm đó chấp nhận được gián đoạn MQTT.

Để chạy API/subscriber trực tiếp trên máy, đặt `MQTT_HOST=localhost`, `MQTT_PORT=1883`, `MQTT_USERNAME` và `MQTT_PASSWORD` trong `.env`.

## Chạy API/subscriber trực tiếp trên máy

Yêu cầu Python 3.12 trở lên và Docker Desktop đang chạy.

1. Tạo `.env` từ `.env.example`.
2. Khởi động PostgreSQL và broker: `docker compose up -d postgres mqtt-broker`.
3. Cài thư viện runtime: `python -m pip install -r backend/requirements.txt`. Để chạy test: `python -m pip install -r backend/requirements-dev.txt`.
4. Mở hai terminal từ repo root và chạy lần lượt `python -m backend.api`, `python -m backend.mqtt_subscriber`. Không chạy subscriber local cùng lúc với service Compose vì cả hai dùng cùng MQTT client ID.
5. Dashboard tích hợp chạy qua Nginx/Compose: `docker compose up -d api dashboard`, rồi mở `http://localhost:8080`. Nginx chuyển `/api/` tới service `api`.

Kết nối Python trực tiếp dùng các biến `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`. Compose ánh xạ cùng `DB_NAME`, `DB_USER`, `DB_PASSWORD` sang cấu hình PostgreSQL và đặt host/port nội bộ cho API/subscriber. `DB_URL` có thể dùng làm DSN ghi đè; mã hóa URL username/password nếu dùng ký tự đặc biệt. Nếu `DB_PASSWORD` chứa `$`, đặt giá trị trong dấu nháy đơn trong `.env` để Compose không nội suy.

## Cơ sở dữ liệu

Các file `backend/migrations/*.sql` được áp dụng một lần theo thứ tự tên file khi API hoặc subscriber khởi động; bảng `schema_migrations` ghi nhận file đã áp dụng. Với database cũ đã có `posture_events`, migration 001 được ghi nhận là đã áp dụng. Migration hiện tại tạo bảng `posture_events` với `event_id` duy nhất, `ts TIMESTAMPTZ`, `seat_id`, `label`, `trunk_angle`, `confidence` và `model_version`; có index theo thời gian và `(seat_id, ts)`.

Không có bước tự chuyển dữ liệu cũ từ SQLite sang PostgreSQL. Nếu đã có bản ghi cần giữ, hãy xuất/nhập dữ liệu bằng một migration riêng trước khi xóa hoặc bỏ volume/database cũ.

## Retention event

Lệnh `python -m backend.retention --days <ngày>` mặc định chỉ đếm số dòng dự kiến xóa. Xóa cần chỉ rõ cả `--apply` và `--confirm-db <tên_database>`; tên xác nhận phải khớp tên database mà cấu hình kết nối đang trỏ tới. Chỉ chạy `--apply` trên database đã được xác nhận là disposable hoặc sau khi nhóm duyệt chính sách retention.

Hiện retention dùng `ts`, là timestamp do đồng hồ máy Vision tạo. Nếu đồng hồ Vision lệch so với thời gian thực hoặc đồng hồ backend, tập dòng đủ điều kiện xóa có thể bị tính sai (xóa sớm hoặc giữ quá lâu). Sau khi migration 002 bổ sung `received_at` được nhóm duyệt và triển khai, dự kiến chuyển retention sang mốc nhận ở backend; chưa có thay đổi schema hay hành vi đó ở hiện tại.

## Kiểm tra và giới hạn

- API mới nhất: `Invoke-RestMethod http://localhost:8000/api/events/latest`
- API lịch sử: `Invoke-RestMethod 'http://localhost:8000/api/events?limit=20'`
- Publisher giả: `python tests/test_mock_publisher.py` (cần broker và dependencies ở trên).
- Kiểm thử backend: cài dev dependencies rồi chạy `python -m pytest tests/test_backend.py tests/test_validator.py -q` (kiểm thử thao tác DB cần PostgreSQL test instance qua `TEST_DATABASE_URL`).

API giới hạn tối đa 500 bản ghi mỗi yêu cầu. Broker luôn bật xác thực; giữ credentials ngoài Git. Dashboard báo khả năng kết nối API; quy tắc báo mất dữ liệu từ camera/broker vẫn phụ thuộc quyết định D-04 và nhịp gửi của TV2.
