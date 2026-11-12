# Quyết định và điểm còn mở

Quy tắc cho agent: mục `OPEN` **không do agent tự chốt**. Dùng giá trị mặc định đề xuất (nếu có), ghi "giả định" trong báo cáo bàn giao, và hỏi con người. Khi con người chốt, cập nhật trạng thái thành `DECIDED` kèm ngày và người chốt, rồi cập nhật hợp đồng tương ứng.

## Điểm mở

| ID | Vấn đề | Mặc định đề xuất | Trạng thái |
| --- | --- | --- | --- |
| D-01 | Enum nhãn tư thế | `upright \| slouching \| leaning \| unknown` | OPEN (chốt ở mốc A) |
| D-02 | Cách tính góc khi hông bị bàn che | Dùng góc vai–tai/cổ so với phương thẳng đứng làm dự phòng; `unknown` nếu cả hai không tin cậy | OPEN |
| D-03 | Cách gán `seat_id` | Vùng ghế định nghĩa trong `config.yaml`, gán theo trung điểm hông/vai | OPEN |
| D-04 | Tín hiệu "mất kết nối" cho dashboard | Cách (a): quá N giây không có event; cách (b): topic heartbeat + MQTT Last Will (cần đổi hợp đồng) | OPEN |
| D-05 | Cổng và đường dẫn của stream (ví dụ cổng 81 `/stream`) | Ghi theo firmware thực tế vào `docs/stream_contract.md` | OPEN |
| D-06 | Polling hay WebSocket cho MVP | Polling (đơn giản hơn) | OPEN |
| D-07 | Stack backend và CSDL | PostgreSQL; backend Python kết nối qua Psycopg 3 | DECIDED (2026-11-09, người dùng chọn) |
| D-08 | Độ dài báo cáo (khoảng 40–60 trang theo ghi chú ảnh) | Xác nhận với giảng viên | OPEN |
| D-09 | Độ phân giải/FPS mặc định | Chốt sau đo ở tuần 3 | OPEN |
| D-10 | QoS, retain của MQTT; chu kỳ gửi hay gửi khi nhãn đổi | QoS 1, không retain; cấu hình được | OPEN |

## Đã chốt (từ tài liệu phân công)
- Ba khối module và cấu trúc thư mục như `ARCHITECTURE.md`.
- Topic mẫu `classroom/posture/events`; JSON mẫu; UTC; góc độ; không gửi ảnh/video.
- Không lưu video thô mặc định; dùng `seat_id`; thu dữ liệu có đồng ý.
- Mọi thay đổi qua PR nhỏ; hợp đồng chung đổi cần cả nhóm duyệt.
- Báo cáo 4 chương, tài liệu tham khảo IEEE.

## Nhật ký quyết định (ADR ngắn)
Thêm dòng mới ở cuối theo mẫu:
`YYYY-MM-DD | ID | Quyết định | Lý do | Người chốt`

2026-11-09 | D-07 | Chọn PostgreSQL làm CSDL backend | Người dùng chọn PostgreSQL; phù hợp lưu event tập trung khi tích hợp | Người dùng (TV3)
