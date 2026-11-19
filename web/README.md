# Dashboard (TV3)

Dashboard HTML/CSS/JavaScript thuần gọi backend API; không kết nối trực tiếp tới PostgreSQL và không cần cài package frontend.

## Chạy

Từ thư mục gốc repo: `docker compose up --build api dashboard`, sau đó mở `http://localhost:8080`. Service `dashboard` chạy `web/app_web.py` bằng Python chuẩn thư viện: phục vụ file tĩnh trong `web/` và proxy các request `/api/...` sang backend cùng origin. `BACKEND_URL` mặc định trong Compose là `http://api:8000`. Dashboard hiện chỉ gọi GET API.

Có thể chạy server cục bộ từ thư mục gốc mà không cài thêm package:

```powershell
$env:BACKEND_URL = "http://localhost:8000"
$env:PORT = "8080"
python web/app_web.py
```

Lệnh này chỉ bind loopback. Mở `http://localhost:8080`. `BACKEND_URL` phải trỏ tới địa chỉ backend có thể truy cập từ tiến trình dashboard.

Với toàn bộ stack Docker Compose (gồm MQTT subscriber), chạy `docker compose up --build`; mở `http://localhost:8080`.

## Hành vi

Hiển thị event mới nhất theo seat, phân bố nhãn bằng thanh tỷ lệ, lịch sử tối đa 100 event, bộ lọc thời gian/seat và trạng thái phản hồi API. Bộ lọc nhập theo giờ Việt Nam (Asia/Ho_Chi_Minh, GMT+7) rồi đổi sang UTC khi gọi API, không phụ thuộc timezone của máy đang mở dashboard. Thời gian hiển thị theo giờ Việt Nam; tooltip giữ ISO-8601 UTC. Danh sách ghế gợi ý theo thứ tự tự nhiên. API hiện không có offset/page, nên phân trang 8 event mỗi trang chỉ áp dụng lên tối đa 100 event gần đây đã tải, không đại diện toàn bộ lịch sử trong database.

Khu vực camera chỉ hỗ trợ ESP32-CAM: nhập URL MJPEG như `http://192.168.1.105/stream`, bấm bắt đầu để xem và bấm dừng để giải phóng stream. Trình duyệt cần truy cập được camera qua mạng. Preview độc lập với pipeline Vision: không chạy pose/inference, không gửi frame lên backend, không publish MQTT và không lưu ảnh/video. Chỉ bật trong môi trường test/demo được phép; không hướng camera vào sinh viên khi chưa có chấp thuận phù hợp. URL chỉ nhận HTTP, hostname hợp lệ và không chứa thông tin đăng nhập. Font giao diện dùng system font cục bộ, không tải từ dịch vụ ngoài.

Giao diện polling tối đa mỗi 2 giây, không gửi request chồng lấn và tạm dừng khi tab bị ẩn. Ngưỡng UI `STALE_AFTER_SECONDS = 10` là giả định tạm dựa trên nhịp Vision hiện tại, chưa phải quyết định occupancy được nhóm duyệt. Dữ liệu cũ vẫn hiển thị mờ, nhưng không tham gia phân bố nhãn hiện tại. Timestamp tương lai hoặc không hợp lệ không được tính là mới và được gắn nhãn riêng. Khi không còn event mới hoặc danh sách rỗng, dashboard nêu rõ rằng không thể phân biệt phòng trống với pipeline dừng. Đây chỉ là tuổi event; không khẳng định ghế đang có người, camera mất kết nối hay pipeline đã dừng. Lỗi API tách biệt với freshness; HTTP 503 là server đã phản hồi nhưng dữ liệu không lấy được. Snapshot endpoint thành công được giữ khi endpoint còn lại lỗi, kèm thời điểm nhận snapshot.
