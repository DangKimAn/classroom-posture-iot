# Thuật ngữ

| Thuật ngữ | Nghĩa trong dự án |
| --- | --- |
| Event / sự kiện | Một bản tin JSON mô tả tư thế của một `seat_id` tại thời điểm `ts` |
| `seat_id` | Mã vị trí ngồi (ví dụ `S01`), thay cho danh tính sinh viên |
| Label / nhãn | Kết quả phân loại tư thế; enum chốt trong `DATA_CONTRACT.md` |
| Keypoint | Điểm khung xương do YOLOv8 Pose trả về (17 điểm kiểu COCO) |
| Trunk angle | Góc thân/lưng so với phương thẳng đứng, đơn vị độ, tính trên ảnh 2D (xấp xỉ) |
| Confidence | Độ tin cậy của kết quả (0–1) |
| MJPEG | Luồng video là chuỗi ảnh JPEG qua HTTP |
| Broker | Máy chủ MQTT trung chuyển bản tin |
| QoS | Mức đảm bảo giao nhận MQTT; QoS 1 có thể giao lặp nên cần chống trùng |
| Hợp đồng (contract) | Tài liệu chung quy định định dạng giữa các module |
| Mock | Thành phần giả cùng giao diện (camera giả, publisher giả) |
| MVP | Bản tối thiểu đủ nghiệm thu |
| Mốc A–E | Các mốc ghép hệ thống, xem `TESTING.md` |
| AIoT | IoT kết hợp suy luận AI |
