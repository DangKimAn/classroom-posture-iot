# Kiểm thử, ghép hệ thống và đo đạc

Nguyên tắc: ghép từng chặng bằng giao diện giả trước, thay bằng thành phần thật sau. Khi lỗi xuất hiện, biết ngay lỗi ở chặng nào.

## Mock chuẩn
- **Camera giả:** server MJPEG phát từ video mẫu đã được đồng ý, cùng giao diện `CAM_STREAM_URL`.
- **Publisher giả:** script gửi JSON đúng hợp đồng, gồm cả ca lỗi (thiếu trường, nhãn lạ, `event_id` trùng).
- **Dữ liệu giả cho UI:** seed ẩn danh vào CSDL.
Mock đặt trong `tests/` hoặc thư mục công cụ của module, không lẫn vào mã chạy thật.

## Mốc ghép

| Mốc | Tuần | Nội dung | Điều kiện qua mốc |
| --- | --- | --- | --- |
| A | 1 | Chốt hợp đồng, nhãn, `seat_id`, biến môi trường, API, cấu trúc thư mục | `docs/data_contract.md`, `docs/api_contract.md` đã review/merge |
| B | 2 | Demo từng phần: stream camera; vision đọc stream/video mẫu; broker+DB/API/UI với JSON mẫu | Mỗi module có lệnh chạy riêng và README |
| C | 3–4 | Vision gửi JSON mẫu → backend xác nhận schema, lưu, hiện UI; sau đó thay bằng inference thật | Có log/ảnh từng chặng; ca lỗi được kiểm |
| D | 5 | End-to-end thật; thử khởi động lại camera/broker/backend | Một lệnh theo README đưa hệ thống lên; lỗi có thông báo |
| E | 6–8 | Thu số đo, sửa lỗi ưu tiên, đóng băng tính năng, đóng gói | Số liệu có điều kiện thử; repo sạch secret; bản demo được tag |

## Ca kiểm thử tối thiểu
Mỗi module có ít nhất 2 ca kiểm thử riêng. Gợi ý:
- `firmware`: stream liên tục ≥10 phút; Wi-Fi ngắt rồi nối lại.
- `vision`: góc hợp lệ; keypoint thiếu; đúng ngưỡng; stream mất rồi hồi phục; publish khi broker tắt.
- `backend`: bản tin hợp lệ được lưu; thiếu trường bị từ chối; `event_id` trùng không lưu lại; reconnect broker; tham số API sai.
- `web`: có dữ liệu; không dữ liệu; backend mất.
Test tích hợp đặt ở `tests/integration/`.

## Phép đo và cách ghi
Mỗi số đo ghi kèm điều kiện: phân giải, FPS, ánh sáng, góc máy, khoảng cách, số mẫu, thiết bị chạy, thời lượng.

| Chỉ số | Cách đo | Ghi chú |
| --- | --- | --- |
| Độ chính xác phân loại | Confusion matrix, precision/recall/F1 theo lớp | Nhãn chuẩn gán trước khi chạy; tập chỉnh ngưỡng khác tập kiểm tra; lớp ít mẫu nêu rõ |
| FPS/độ trễ suy luận | Đo trong `vision/` | Ghi CPU/GPU |
| Độ trễ đầu-cuối | Từ lúc chụp khung hình đến khi dashboard hiển thị | Đồng bộ đồng hồ các máy trước khi đo; ghi rõ điểm đo, là ước lượng |
| Tỷ lệ mất sự kiện | Số event đã publish (log vision) so với số đã lưu | Trừ bản tin cố ý bị loại |
| Độ ổn định | Chạy liên tục thời lượng định trước, đếm lần đứt và thời gian phục hồi | Ghi thời lượng |
| Camera | Tỷ lệ mất khung, độ trễ quan sát, nhiệt/nguồn, phục hồi | Ghi 2–3 mức phân giải/FPS |

Agent không tự điền số đo. Nếu không thể đo (thiếu phần cứng), ghi "chưa đo" và nêu cách đo.

## Debug theo chiều dữ liệu
Stream mở được? → vision có in event? → broker thấy bản tin (client subscribe thử)? → DB có dòng? → API trả dữ liệu? → UI hiển thị? Chặng đầu tiên không đạt là chỗ cần sửa.

## Checklist demo cuối kỳ
- [ ] Camera vào Wi-Fi, phát luồng; có cách khởi động lại nếu stream đứt
- [ ] Vision hiển thị keypoint/nhãn/góc ở chế độ debug và gửi event đúng schema
- [ ] Backend lưu bản tin hợp lệ, từ chối bản tin sai; dashboard có dữ liệu mới và lịch sử
- [ ] Trình bày được cách đo chỉ số, FPS/độ trễ, giới hạn, điều kiện thử
- [ ] README chạy được trên máy demo; `.env` tạo từ mẫu; repo không có mật khẩu, video riêng tư, danh tính
- [ ] Đã thử mạng nơi trình bày; có phương án dự phòng được phép nếu Wi-Fi chặn thiết bị
