---
name: start-task
description: Quy trình chuẩn để agent nhận và thực hiện một nhiệm vụ/issue trong repo đồ án IoT tư thế ngồi: xác nhận phạm vi, kiểm tra ranh giới module, đọc đúng tài liệu, làm bản nhỏ nhất, tự kiểm, và bàn giao bằng mẫu báo cáo. Dùng skill này mỗi khi được giao một issue, một tính năng, một lỗi cần sửa, hoặc một đầu việc tài liệu/kiểm thử trong repo này, kể cả khi yêu cầu chỉ là một câu ngắn như "làm giúp tôi cái publisher MQTT".
---

# Bắt đầu một nhiệm vụ

Mục tiêu: làm đúng việc, đúng chỗ, có bằng chứng, để người khác không phải dọn lại. Quy tắc cứng nằm ở `AGENTS.md`; skill này là thao tác cụ thể.

## Bước 1: Xác định nhiệm vụ
- Lấy: đầu ra mong đợi, tiêu chí chấp nhận, nhãn module. Thiếu thì hỏi hoặc ghi giả định.
- Đối chiếu `docs/agent/SCOPE.md`: việc này trong hay ngoài phạm vi? Ngoài phạm vi thì dừng và báo.

## Bước 2: Chọn tài liệu cần đọc (đừng đọc hết)
- Chạm event/topic/DB/API/biến môi trường → `DATA_CONTRACT.md`.
- Viết code/tài liệu → `CONVENTIONS.md`.
- Chạm dữ liệu, ảnh, secret, log → `SECURITY_PRIVACY.md`.
- Cần test/đo → `TESTING.md`.
- Gặp điều chưa rõ → tra `DECISIONS.md` xem đã chốt hay còn `OPEN`.

## Bước 3: Kiểm tra ranh giới
Liệt kê file dự định sửa. Tất cả phải nằm trong đường dẫn của module (bảng ở `WORKFLOW.md` §2). Có file ngoài module → dừng; dùng mock hoặc đề xuất issue riêng. Nếu cần đổi hợp đồng → chuyển sang skill `change-contract`.

## Bước 4: Làm nhỏ nhất chạy được
Cài tối thiểu trước, kèm test/README cùng module. Dùng mock cho phần phụ thuộc chưa có (camera giả, publisher giả, dữ liệu giả). Không thêm tính năng ngoài issue; ghi thành đề xuất.

## Bước 5: Tự kiểm
- Chạy test và lệnh theo README; ghi kết quả thật.
- Đối chiếu từng tiêu chí chấp nhận.
- Quét diff: có secret, dữ liệu nhận dạng, video, trọng số lớn, file ngoài module không?
- Phần phụ thuộc phần cứng không truy cập được thì ghi "chưa kiểm chứng" và nêu cách kiểm.

## Bước 6: Bàn giao
Điền mẫu ở `AGENTS.md` §5. Cập nhật README/tài liệu bị ảnh hưởng. Đề xuất tên nhánh/commit theo `CONVENTIONS.md`.

## Lỗi hay gặp
- Tự "tiện tay" sửa file module khác để chạy được.
- Báo xong khi chưa chạy.
- Điền số đo hoặc tài liệu tham khảo không có thật.
- Đổi tên trường event cho "gọn" mà không qua hợp đồng.
