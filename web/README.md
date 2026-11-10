# Dashboard (TV3)

Dashboard HTML/CSS/JavaScript thuần gọi backend API; không kết nối trực tiếp tới PostgreSQL và không cần cài package frontend.

## Chạy

Từ thư mục gốc repo: `docker compose up --build api dashboard`, sau đó mở `http://localhost:8080`. Nginx phục vụ file tĩnh và proxy `/api/` sang API cùng origin. `python -m http.server` chỉ phục vụ file tĩnh, không proxy API, nên không dùng riêng lệnh đó để chạy dashboard tích hợp.

Với toàn bộ stack Docker Compose (gồm MQTT subscriber), chạy `docker compose up --build`; mở `http://localhost:8080`.

## Hành vi

Hiển thị event mới nhất theo seat, phân bố nhãn bằng thanh tỷ lệ, lịch sử tối đa 100 event, bộ lọc thời gian/seat và trạng thái khả dụng của API. Bộ lọc thời gian nhập theo UTC; thời gian hiển thị theo giờ Việt Nam, tooltip giữ ISO-8601 UTC. Danh sách ghế gợi ý từ dữ liệu API. Dữ liệu chỉ gồm mã vị trí và thông tin event, không có ảnh/video hay danh tính.

Giao diện polling tối đa mỗi 2 giây, không gửi request chồng lấn và tạm dừng khi tab bị ẩn. D-06 vẫn cần nhóm xác nhận. Trạng thái hiển thị phản ánh khả năng gọi API, không khẳng định tình trạng camera hoặc pipeline.
