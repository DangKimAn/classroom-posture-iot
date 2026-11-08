# Phạm vi (Scope)

Mục đích file này: để agent biết việc nào **được làm**, việc nào **không**, và cách xử lý khi nằm giữa. Khi không chắc, coi là ngoài phạm vi và hỏi.

## Trong phạm vi (MVP)
- Luồng video từ ESP32-CAM qua HTTP/Wi-Fi (MJPEG) trong mạng thử nghiệm.
- Đọc luồng, suy luận YOLOv8 Pose, tính góc thân/lưng, phân loại nhãn tư thế bằng ngưỡng cấu hình, làm mượt theo thời gian.
- Phát sự kiện JSON qua MQTT theo hợp đồng.
- Backend: nhận, kiểm tra, loại trùng, lưu CSDL; REST API.
- Dashboard web: trạng thái mới nhất, lịch sử có lọc theo thời gian/`seat_id`, biểu đồ, trạng thái mất kết nối.
- Đo đạc: độ chính xác theo lớp, FPS/độ trễ, độ trễ đầu-cuối, tỷ lệ mất sự kiện, độ ổn định.
- Báo cáo 4 chương, sơ đồ, slide, README, `.env.example`, dữ liệu thử ẩn danh.

## Ngoài phạm vi (không làm nếu chưa có phê duyệt)
- Nhận dạng danh tính sinh viên (nhận diện khuôn mặt, gắn tên/MSSV).
- Lưu hoặc truyền video/ảnh thô; ghi hình mặc định.
- Đánh giá sức khỏe, mức độ tập trung, thái độ học tập, điểm số hay xếp hạng sinh viên.
- Huấn luyện/tinh chỉnh model lớn từ dữ liệu lớp học thật (dùng model có sẵn; huấn luyện lại chỉ khi nhóm quyết định).
- Triển khai lên đám mây công khai, mở dịch vụ ra Internet, hệ thống đăng nhập đa người dùng phức tạp.
- Hỗ trợ nhiều camera/nhiều phòng ngoài những gì hợp đồng quy định.
- Tối ưu hóa phần cứng ngoài ESP32-CAM, thiết kế vỏ/mạch.
- Tự thu dữ liệu từ người thật khi chưa có sự đồng ý theo quy định lớp/môn.

## Vùng xám: cách xử lý
| Tình huống | Hành động |
| --- | --- |
| Tính năng "hay hơn" nhưng không có trong issue | Ghi thành đề xuất trong báo cáo bàn giao, không làm |
| Cần sửa file module khác để việc chạy được | Dừng, mở issue/PR riêng, hoặc dùng mock |
| Cần thêm trường vào event | Dùng skill `change-contract` |
| Cần dữ liệu thật để thử | Dùng video/dữ liệu mẫu đã được đồng ý hoặc dữ liệu giả; hỏi con người |

## Quy tắc ranh giới module
Module chỉ sửa file trong thư mục của mình và test liên quan (bảng ở `WORKFLOW.md` §2). Lý do: ba người làm song song, hai người sửa cùng file là nguồn xung đột lớn nhất. Hợp đồng chung chỉ đổi qua quy trình riêng.

## Sản phẩm bàn giao (deliverables)
Repo chạy được theo README; sơ đồ kiến trúc; `docs/data_contract.md`, `docs/api_contract.md`; bảng kết quả đo; báo cáo; slide; bản tag demo.
