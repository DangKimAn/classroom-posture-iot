# Hướng dẫn chạy backend và dashboard (TV3)

## Chạy toàn bộ stack bằng Docker Compose

1. Cài và khởi động Docker Desktop.
2. Từ thư mục gốc repo, tạo `.env` từ `.env.example`. Mật khẩu mẫu chỉ dùng cho máy local; thay mật khẩu nếu dùng môi trường chung. Không commit `.env`.
3. Chạy `docker compose up --build`.
4. Mở dashboard tại `http://localhost:8080`.

Compose khởi động Mosquitto, PostgreSQL, API, MQTT subscriber và Nginx phục vụ web. API và subscriber là hai service riêng dùng chung image backend. Dashboard được Nginx phục vụ tại `http://localhost:8080`; Nginx proxy `/api/` sang service `api`, nên cùng origin và không cần CORS. PostgreSQL và Mosquitto lưu dữ liệu trong các named volume `posture_pgdata` và `mosquitto_data`; `docker compose down` giữ các volume. Chỉ xóa volume khi chủ ý xóa dữ liệu. Các cổng host chỉ bind loopback.

## Chạy API/subscriber trực tiếp trên máy

Yêu cầu Python 3.12 trở lên và Docker Desktop đang chạy.

1. Tạo `.env` từ `.env.example`.
2. Khởi động PostgreSQL và broker: `docker compose up -d postgres mqtt-broker`.
3. Cài thư viện runtime: `python -m pip install -r backend/requirements.txt`. Để chạy test: `python -m pip install -r backend/requirements-dev.txt`.
4. Mở hai terminal từ repo root và chạy lần lượt `python -m backend.api`, `python -m backend.mqtt_subscriber`. Không chạy subscriber local cùng lúc với service Compose vì cả hai dùng cùng MQTT client ID.
5. Dashboard tích hợp chạy qua Nginx/Compose: `docker compose up -d api dashboard`, rồi mở `http://localhost:8080`. Nginx chuyển `/api/` tới service `api`.

Kết nối Python trực tiếp dùng các biến `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`. Compose ánh xạ cùng `DB_NAME`, `DB_USER`, `DB_PASSWORD` sang cấu hình PostgreSQL và đặt host/port nội bộ cho API/subscriber. `DB_URL` có thể dùng làm DSN ghi đè; mã hóa URL username/password nếu dùng ký tự đặc biệt. Nếu `DB_PASSWORD` chứa `$`, đặt giá trị trong dấu nháy đơn trong `.env` để Compose không nội suy.

## Cơ sở dữ liệu

Các file `backend/migrations/*.sql` được áp dụng theo thứ tự tên file khi API hoặc subscriber khởi động. Migration hiện tại tạo bảng `posture_events` với `event_id` duy nhất, `ts TIMESTAMPTZ`, `seat_id`, `label`, `trunk_angle`, `confidence` và `model_version`; có index theo thời gian và `(seat_id, ts)`.

Không có bước tự chuyển dữ liệu cũ từ SQLite sang PostgreSQL. Nếu đã có bản ghi cần giữ, hãy xuất/nhập dữ liệu bằng một migration riêng trước khi xóa hoặc bỏ volume/database cũ.

## Kiểm tra và giới hạn

- API mới nhất: `Invoke-RestMethod http://localhost:8000/api/events/latest`
- API lịch sử: `Invoke-RestMethod 'http://localhost:8000/api/events?limit=20'`
- Publisher giả: `python tests/test_mock_publisher.py` (cần broker và dependencies ở trên).
- Kiểm thử backend: cài dev dependencies rồi chạy `python -m pytest tests/test_backend.py tests/test_validator.py -q` (kiểm thử thao tác DB cần PostgreSQL test instance qua `TEST_DATABASE_URL`).

API giới hạn tối đa 500 bản ghi mỗi yêu cầu. Broker anonymous chỉ dành cho phát triển trên loopback, không dùng trên LAN/lớp học hoặc Internet. Môi trường dùng chung cần bật xác thực Mosquitto và dùng credentials ngoài Git. Dashboard báo khả năng kết nối API; quy tắc báo mất dữ liệu từ camera/broker vẫn phụ thuộc quyết định D-04 và nhịp gửi của TV2.
