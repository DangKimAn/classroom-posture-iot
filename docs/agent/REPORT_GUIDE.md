# Hướng dẫn cho agent khi viết báo cáo/slide

## Bố cục
1. Tổng quan và cơ sở lý thuyết: bài toán, phạm vi, IoT/AIoT, ESP32-CAM, Wi-Fi, HTTP/MQTT, YOLOv8 Pose, góc tư thế, lưu trữ, ứng dụng học đường.
2. Đề xuất mô hình và thiết kế: yêu cầu, kiến trúc, luồng dữ liệu, thiết kế từng module, hợp đồng giao tiếp, bảo mật và quyền riêng tư.
3. Kết quả thực nghiệm và thảo luận: thiết lập thử, dữ liệu mẫu, chỉ số, bảng/biểu đồ, kết quả, lỗi, giới hạn, so với mục tiêu.
4. Kết luận và hướng phát triển.
Tài liệu tham khảo: IEEE.
Độ dài (khoảng 40–60 trang theo ghi chú ảnh) chưa được xác nhận chính thức (D-08); ưu tiên nội dung thực nghiệm hơn kéo dài lý thuyết.

## Quy tắc
- Nội dung phải khớp với mã và `docs/` hiện có; nguồn số liệu là log/file đo thật.
- Mỗi bảng/biểu đồ ghi điều kiện thử và trỏ tới nguồn.
- Nêu giới hạn: góc 2D là xấp xỉ, lớp ít mẫu, hông bị bàn che, ảnh hưởng ánh sáng/góc máy.
- Không tuyên bố hệ thống đánh giá sức khỏe/tập trung/thái độ học tập.
- Có mục quyền riêng tư và đạo đức (xem `SECURITY_PRIVACY.md`).
- Thuật ngữ nhất quán (xem `GLOSSARY.md`); hình có số và chú thích.

## Trích dẫn IEEE
Đánh số theo thứ tự xuất hiện `[1]`, `[2]`. Không bịa nguồn; chỉ đưa tài liệu đã xác minh được (tác giả, năm, venue). Không xác minh được thì để trống và báo con người tra.
- Bài báo: `[1] A. Author, B. Author, "Title," Abbrev. Journal, vol. x, no. x, pp. xx–xx, year.`
- Hội nghị: `[2] A. Author, "Title," in Proc. Conf., City, year, pp. xx–xx.`
- Trang web: `[3] Org., "Title," Year. [Online]. Available: URL`

## Sơ đồ nên có
Kiến trúc tổng thể; luồng camera → CV → MQTT → DB → API → UI; sơ đồ nối nguồn/board; sơ đồ bảng CSDL; sơ đồ tuần tự một sự kiện; ảnh dashboard không nhạy cảm.
