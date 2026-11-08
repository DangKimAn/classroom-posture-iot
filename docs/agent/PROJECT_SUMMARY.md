# Tóm tắt dự án (đọc 1 phút)

## Là gì
Hệ thống IoT/AIoT nhận biết **tư thế ngồi** của sinh viên trong lớp học từ camera, rồi hiển thị trạng thái và lịch sử trên dashboard. Đây là đồ án cuối môn IoT năm 4, nhóm 3 người, thời gian tham khảo 8 tuần.

## Chạy như thế nào (một dòng)
`ESP32-CAM` phát video MJPEG qua Wi-Fi → dịch vụ Python (`OpenCV` + `YOLOv8 Pose`) lấy keypoint, tính góc thân/lưng, gán nhãn → gửi **sự kiện JSON** (không có ảnh) qua `MQTT` → backend kiểm tra và lưu vào CSDL → API → dashboard web.

## Ba khối và thư mục

| Khối | Thư mục | Việc chính |
| --- | --- | --- |
| Thiết bị & luồng video | `firmware/` | ESP32-CAM, Wi-Fi, MJPEG qua HTTP, đo độ ổn định |
| Thị giác máy tính | `vision/` | Đọc stream, pose, góc, nhãn, publish MQTT, đánh giá |
| Dữ liệu & giao diện | `backend/`, `web/` | Broker, subscriber, DB, API, dashboard |
| Tài liệu / kiểm thử | `docs/`, `tests/` | Báo cáo, hợp đồng, test tích hợp |

## Điều quan trọng nhất cần nhớ
1. Các khối nói chuyện với nhau **chỉ qua hợp đồng** trong `DATA_CONTRACT.md`.
2. **Không gửi/lưu ảnh hay video**, không có danh tính sinh viên; dùng `seat_id`.
3. Nhãn tư thế là kết quả ngưỡng góc thực nghiệm, **không phải đánh giá sức khỏe hay thái độ học tập**.
4. Mọi số đo trong báo cáo phải đến từ lần đo thật, kèm điều kiện thử.
5. `main` luôn chạy được; mọi thay đổi qua Pull Request nhỏ.

## Kết quả cần có khi nghiệm thu
Camera truyền luồng qua Wi-Fi; CV tạo nhãn + góc + confidence; event MQTT được lưu và hiển thị gần thực thời + lịch sử có lọc; có số đo thật (confusion matrix/precision-recall theo lớp, độ trễ đầu-cuối, tỷ lệ mất sự kiện, thời gian chạy ổn định) kèm điều kiện và giới hạn; có hướng dẫn cài đặt, sơ đồ kiến trúc, schema/API, dữ liệu thử ẩn danh; repo sạch secret.

## Mốc lớn
Tuần 1 chốt hợp đồng → tuần 2 demo từng phần → tuần 3–4 hoàn thiện module + kiểm tra giao diện → tuần 5 end-to-end → tuần 6 đánh giá → tuần 7 báo cáo, đóng băng tính năng → tuần 8 diễn tập, tag bản demo. Chi tiết: `TESTING.md`.

## Đọc tiếp
Phạm vi: `SCOPE.md` · Hợp đồng: `DATA_CONTRACT.md` · Quy chuẩn: `CONVENTIONS.md` · Chưa chốt: `DECISIONS.md`.
