# AGENTS.md — Giao thức làm việc cho agent

Đồ án IoT năm 4: **phát hiện tư thế ngồi của sinh viên trong lớp học** (ESP32-CAM → OpenCV/YOLOv8 Pose → MQTT → backend/CSDL → dashboard).
File này là điểm vào duy nhất. Đọc xong file này là đủ để bắt đầu; đọc thêm tài liệu khác chỉ khi nhiệm vụ cần.

## 1. Thứ tự đọc (dừng khi đã đủ thông tin)

| Mức | File | Khi nào đọc |
| --- | --- | --- |
| 0 | `AGENTS.md` (file này) | Luôn luôn (Điểm vào duy nhất) |
| 1 | `docs/BUSINESS.md` & `docs/agent/PROJECT_SUMMARY.md` | Hiểu bài toán, bối cảnh lớp học, định nghĩa các nhãn tư thế và ca sử dụng |
| 2 | `docs/FLOWS.md` | Khi cần nắm luồng dữ liệu liên khối (Camera → Vision → MQTT → DB → Web) |
| 3 | `docs/RULES.md` & `docs/agent/SCOPE.md` | Trước khi nhận việc: kiểm tra quy tắc cứng, ranh giới module, bảo mật, DoD |
| 4 | `docs/TECHS.md` & `docs/agent/DATA_CONTRACT.md` | Khi đụng công nghệ, thư viện, topic MQTT, JSON schema, CSDL, REST API |
| 5 | `docs/agent/CONVENTIONS.md` | Trước khi viết code, đặt tên biến/hàm, viết test hoặc commit |
| 6 | `docs/agent/WORKFLOW.md` | Khi tạo nhánh, mở PR, review code, phân quyền thư mục |
| 7 | `docs/agent/SECURITY_PRIVACY.md` | Khi đụng dữ liệu, mật khẩu Wi-Fi/Broker, ảnh/video, log |
| 8 | `docs/agent/TESTING.md` | Khi viết test, chạy mock dữ liệu, đo đạc chỉ số, chuẩn bị demo |
| 9 | `docs/agent/ARCHITECTURE.md`, `GLOSSARY.md`, `REPORT_GUIDE.md` | Khi cần chi tiết sâu/thuật ngữ/soạn báo cáo IEEE 4 chương |
| — | `docs/agent/DECISIONS.md` | Khi gặp điều chưa rõ: xem đã có quyết định (`DECIDED`) hay còn mở (`OPEN`) |

## 2. Quy tắc cứng (không có ngoại lệ nếu chưa có phê duyệt của con người)

1. **Đúng phạm vi.** Chỉ làm việc nằm trong issue được giao và trong thư mục của module đó (xem `WORKFLOW.md` §2). Ngoài phạm vi → dừng, báo cáo, đề xuất issue.
2. **Hợp đồng là luật.** Không tự đổi topic MQTT, schema JSON, tên trường, enum nhãn, bảng DB, đường dẫn API. Muốn đổi → dùng skill `change-contract`.
3. **Không bịa.** Không bịa số đo, kết quả đánh giá, tài liệu tham khảo, hành vi của thiết bị. Chưa đo thì ghi "chưa đo". Không xác minh được thì nói rõ.
4. **Không lộ bí mật, không lộ danh tính.** Không commit `.env`, mật khẩu Wi-Fi, khóa broker, video lớp học, dữ liệu nhận dạng, trọng số lớn. Không ghi tên/MSSV sinh viên vào dữ liệu, log, ví dụ.
5. **Không tự quyết điều đang mở.** Các mục trong `DECISIONS.md` trạng thái `OPEN` cần con người chốt. Làm theo mặc định đề xuất nếu có, đánh dấu rõ giả định, và hỏi.
6. **Không sửa lịch sử/hành động khó đảo ngược** (force-push, xóa nhánh, xóa dữ liệu, `git filter-repo`) nếu chưa được yêu cầu rõ.
7. **Có bằng chứng.** Mỗi thay đổi phải kèm cách chạy và kết quả kiểm tra thật (log/lệnh/test). Không báo "xong" khi chưa chạy.

## 3. Vòng làm việc chuẩn của một nhiệm vụ

1. **Hiểu:** đọc issue, `SCOPE.md`, phần liên quan của hợp đồng. Xác nhận đầu ra và tiêu chí chấp nhận. Có điểm mơ hồ ảnh hưởng hợp đồng → hỏi trước khi code.
2. **Lập kế hoạch ngắn:** liệt kê file sẽ sửa; kiểm tra tất cả đều thuộc module được giao.
3. **Làm nhỏ nhất chạy được** trước, kèm test/README cùng module.
4. **Tự kiểm:** chạy test, chạy lệnh theo README, đối chiếu tiêu chí chấp nhận và `SECURITY_PRIVACY.md`.
5. **Bàn giao** bằng mẫu ở §5. Cập nhật tài liệu bị ảnh hưởng.

Skill hỗ trợ: `.claude/skills/start-task`, `change-contract`, `review-pr`.

## 4. Khi nào phải dừng và hỏi con người
- Cần đổi hợp đồng hoặc đụng module khác.
- Yêu cầu mâu thuẫn giữa issue và tài liệu trong `docs/agent/`.
- Việc cần dữ liệu thật của sinh viên, ảnh/video lớp học, hoặc thông tin đăng nhập.
- Một mục `OPEN` trong `DECISIONS.md` chặn tiến độ.
- Thiết bị/phần cứng không truy cập được (agent không thể tự kiểm chứng) → nói rõ phần nào chưa kiểm chứng được.

## 5. Mẫu báo cáo bàn giao (cuối mỗi nhiệm vụ)

```
Issue: #<số> — <tên>
Đã làm: <1–3 dòng>
File đã sửa/tạo: <danh sách>
Cách chạy/kiểm thử: <lệnh>
Kết quả kiểm thử: <log/số liệu thật, hoặc "chưa kiểm chứng: lý do">
Ảnh hưởng hợp đồng chung: Có/Không
Giả định đã dùng: <nếu có>
Việc còn lại / rủi ro: <nếu có>
```

## 6. Ngôn ngữ
- Giao tiếp với nhóm, tài liệu `docs/`, báo cáo: **tiếng Việt** (giữ thuật ngữ kỹ thuật tiếng Anh).
- Mã nguồn, tên biến/hàm/file, commit message, tên nhánh, log: **tiếng Anh**.
