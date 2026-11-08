# Bảo mật và quyền riêng tư

Dữ liệu của dự án phản ánh hành vi của người thật trong lớp học. Mặc định là thu và giữ ít nhất có thể. Các quy tắc dưới đây áp dụng cho mọi module và mọi agent.

## Bắt buộc
1. **Không danh tính.** Dùng `seat_id`. Không tên, MSSV, khuôn mặt nhận diện trong dữ liệu, log, ví dụ, ảnh minh họa.
2. **Không video/ảnh thô được lưu hoặc gửi đi.** Khung hình chỉ tồn tại trong bộ nhớ để suy luận. Event MQTT chỉ là JSON theo hợp đồng. Chế độ debug có hiển thị khung hình chỉ chạy cục bộ và không ghi ra đĩa mặc định.
3. **Chỉ thu dữ liệu cần thiết**, có thông báo và đồng ý theo quy định lớp/môn. Dữ liệu thử đã ẩn danh.
4. **Giới hạn truy cập và thời hạn lưu** (ghi trong `docs/backend_setup.md`). Broker bật xác thực, không mở ra mạng ngoài lớp thử.
5. **Không commit:** `.env`, mật khẩu Wi-Fi (`secrets.h`), khóa/mật khẩu broker, video lớp học, dữ liệu nhận dạng, trọng số lớn (trừ khi nhóm thống nhất).
6. **Ý nghĩa của nhãn:** là kết quả ngưỡng góc thực nghiệm. Không viết hay hiển thị như đánh giá sức khỏe, mức độ tập trung hay thái độ học tập.
7. **Backend coi mọi bản tin MQTT là không đáng tin:** validate schema, giới hạn kích thước, tham số hóa truy vấn SQL, giới hạn số bản ghi API.

## Khi phát hiện vi phạm
- Bí mật bị commit: dừng, báo con người, đề xuất đổi khóa/mật khẩu ngay; việc dọn lịch sử chỉ làm khi được yêu cầu.
- Dữ liệu nhận dạng hoặc video nằm trong repo: dừng, báo, không đẩy tiếp.

## Khi được yêu cầu thứ vi phạm
Giải thích ngắn lý do, đề xuất phương án thay thế (dữ liệu giả, video mẫu đã được đồng ý, ảnh ẩn danh/làm mờ, bật debug cục bộ), và hỏi lại.

## Ảnh và minh họa cho báo cáo
Ảnh có người cần được cho phép hoặc làm mờ. Ưu tiên ảnh dashboard, sơ đồ, ảnh thiết bị.
