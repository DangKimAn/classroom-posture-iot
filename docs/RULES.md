# RULES.md — Bộ Quy Tắc Kỹ Thuật & Ràng Buộc Hệ Thống

Tài liệu quy định các luật bất biến (Invariants) mà mọi thành viên và AI Agent bắt buộc phải tuân thủ tuyệt đối trong suốt vòng đời dự án.

---

## 1. Bảy Quy Tắc Bất Khả Xâm Phạm (Hard Rules)

1. **Tuân thủ đúng ranh giới thư mục (Strict Scoping)**:
   - Chỉ được tạo và chỉnh sửa file trong thư mục module được phân công (xem Mục 2).
   - Nghiêm cấm tự ý sửa file của module khác với lý do "sửa tiện tay để test chạy được".
2. **Hợp đồng dữ liệu là luật tối thượng (Contract Immutability)**:
   - Topic MQTT, cấu trúc JSON payload, bảng CSDL và API endpoint là nguồn sự thật duy nhất.
   - Không được tự ý đổi tên trường, thêm trường bắt buộc, hoặc đổi đơn vị đo nếu chưa qua quy trình RFC (`change-contract`).
3. **Tuyệt đối không bịa số đo (Zero Hallucination)**:
   - Các chỉ số đo đạc (FPS, độ trễ đầu-cuối, ma trận nhầm lẫn, tỷ lệ mất gói) trong báo cáo bắt buộc phải đến từ lần đo thực tế trên phần cứng thật.
   - Chưa đo được do thiếu thiết bị thì phải ghi rõ: `"Chưa kiểm chứng do thiếu phần cứng"`.
4. **Bảo mật và Quyền riêng tư tuyệt đối (Privacy & Security)**:
   - Nghiêm cấm commit file `.env`, `secrets.h`, khóa MQTT, token.
   - Tuyệt đối không lưu trữ video, ảnh thô hay khuôn mặt sinh viên.
   - Chỉ sử dụng mã vị trí ghế (`seat_id`), không dùng tên hoặc MSSV.
5. **Không tự quyết định các vấn đề đang mở (No Assumption on OPEN decisions)**:
   - Các vấn đề có trạng thái `OPEN` trong [docs/agent/DECISIONS.md](file:///home/na/code/final_iot/docs/agent/DECISIONS.md) phải do nhóm con người chốt trước khi áp dụng vào code.
6. **Không phá vỡ lịch sử Git (Git Safety)**:
   - Cấm force-push (`git push -f`), cấm xóa nhánh `main` hoặc `develop`, cấm viết lại lịch sử commit.
7. **Bàn giao kèm bằng chứng thực tế (Proof of Work)**:
   - Mỗi Pull Request hoặc nhiệm vụ hoàn thành phải đi kèm log chạy thực tế hoặc test case chứng minh tính đúng đắn.

---

## 2. Ma Trận Phân Quyền Theo Đường Dẫn (Path-Based Ownership)

| Module (Nhãn Issue) | Chủ sở hữu | Đường dẫn ĐƯỢC PHÉP sửa | Đường dẫn NGHIÊM CẤM sửa |
| :--- | :---: | :--- | :--- |
| `firmware` | **TV1** | `firmware/`, `tests/mocks/camera*` | `vision/`, `backend/`, `web/` |
| `vision` | **TV2** | `vision/`, `tests/test_vision*`, `tests/test_classifier.py` | `firmware/`, `backend/`, `web/` |
| `backend` | **TV3** | `backend/`, `docker-compose.yml`, `mosquitto.conf`, `tests/test_backend*`, `tests/test_validator.py` | `firmware/`, `vision/`, `web/` |
| `web` | **TV3** | `web/`, `tests/test_ui*` | `firmware/`, `vision/`, `backend/` |
| `contract` | **Cả 3 người** | `docs/data_contract.md`, `docs/agent/DATA_CONTRACT.md` | Chỉ sửa qua PR riêng được cả 3 approve |
| `docs` | **Theo phân công** | File chương phụ trách trong `docs/` | Không sửa đè file do thành viên khác viết |

---

## 3. Quy Chuẩn Kỹ Thuật & Dữ Liệu (Technical Constraints)

1. **Thời gian**: Bắt buộc dùng múi giờ chuẩn quốc tế **UTC**, định dạng **ISO-8601** có đuôi `Z` (ví dụ: `2026-11-08T03:12:45Z`). Không dùng giờ local của máy tính phát tin.
2. **Góc nghiêng**: Đơn vị tính là **độ (°)**, làm tròn đến 1–2 chữ số thập phân, phạm vi hình học từ $0^\circ$ đến $90^\circ+$.
3. **Mã ghế**: Định dạng chuỗi ngắn gọn, duy nhất trong phòng học (ví dụ: `S01`, `S02`, `B1-05`).
4. **Định dạng code**:
   - Python: Tuân thủ chuẩn PEP 8, có type hints cho hàm công khai, bọc exception rõ ràng, không nuốt lỗi `except: pass`.
   - C/C++ Arduino: Định nghĩa hằng số bằng chữ in hoa, in trạng thái kết nối rõ ràng qua cổng Serial.
5. **Quy chuẩn đặt tên nhánh & Commit**:
   - Nhánh: `feature/<module>-<mô-tả>-#<issue>` (ví dụ: `feature/vision-yolo-pose-#12`).
   - Commit: `<type>(<module>): <mô tả ngắn> #<issue>` (ví dụ: `feat(backend): add deduplication query #14`).

---

## 4. Tiêu Chuẩn Hoàn Thành (Definition of Done - DoD)

Một issue/tính năng chỉ được phép đóng và merge vào `develop` khi đạt đủ **6 tiêu chí**:
- [ ] Code chạy được theo hướng dẫn trong `README.md` của module đó trên máy sạch.
- [ ] Vượt qua toàn bộ Unit Tests trong thư mục `tests/`.
- [ ] Không có file secret, file video/ảnh hay trọng số lớn (`.pt`, `.task`) trong diff commit.
- [ ] Không chỉnh sửa lấn sang thư mục của module khác.
- [ ] Đã cập nhật tài liệu hoặc README tương ứng nếu có thay đổi cách chạy.
- [ ] Được ít nhất 1 thành viên khác review và bấm **Approve** trên Pull Request.
