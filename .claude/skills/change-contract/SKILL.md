---
name: change-contract
description: Quy trình đề xuất và thực hiện thay đổi hợp đồng dữ liệu của đồ án IoT tư thế ngồi: topic MQTT, schema JSON event, enum nhãn, bảng posture_events, đường dẫn/tham số API, biến môi trường dùng chung. Dùng skill này mỗi khi cần thêm/sửa/xóa một trường event, đổi tên topic, thêm nhãn mới, thêm heartbeat/status, đổi API, hoặc phát hiện hai module hiểu hợp đồng khác nhau, kể cả khi người dùng chỉ nói "thêm trường X vào event".
---

# Thay đổi hợp đồng dữ liệu

Hợp đồng là chỗ ba module gặp nhau. Một thay đổi nhỏ ở đây có thể làm bản tin của module khác bị loại âm thầm, nên mọi thay đổi đi qua quy trình riêng. Agent **không** sửa hợp đồng như một phần phụ của việc khác.

## Khi nào áp dụng
Thay đổi bất kỳ thứ gì trong `docs/agent/DATA_CONTRACT.md`, `docs/data_contract.md`, `docs/api_contract.md`: tên topic, QoS/retain, tên/kiểu/đơn vị trường, enum nhãn, schema bảng, endpoint, tham số, biến môi trường chung.

## Quy trình
1. **Dừng việc đang làm** nếu nó phụ thuộc vào thay đổi; làm tiếp bằng mock theo hợp đồng hiện tại.
2. **Viết đề xuất** (issue riêng, nhãn `contract`) gồm:
   - Vấn đề: vì sao hợp đồng hiện tại không đủ.
   - Thay đổi đề xuất: diff cụ thể (trước/sau) của JSON, SQL hoặc API.
   - Ảnh hưởng: module nào phải sửa (`firmware`, `vision`, `backend`, `web`), dữ liệu đã lưu có cần migrate không.
   - Tương thích: ưu tiên thêm trường tùy chọn thay vì đổi nghĩa trường cũ.
   - Phương án thay thế đã cân nhắc.
3. **Xin duyệt của cả ba người** (con người). Agent không tự coi là đã duyệt.
4. **Sau khi duyệt, một PR riêng** chỉ chứa thay đổi hợp đồng: cập nhật `docs/data_contract.md`/`docs/api_contract.md`, `docs/agent/DATA_CONTRACT.md`, JSON mẫu, và (nếu cần) mục trong `docs/agent/DECISIONS.md`.
5. **Sau khi merge**, các module cập nhật code qua PR riêng của từng module, với test dùng JSON mẫu mới.

## Kiểm tra trước khi đề xuất
- Có thể đạt mục tiêu mà không đổi hợp đồng không (ví dụ tính ở phía nhận)?
- Có đang tạo trường chứa danh tính/ảnh không? Nếu có thì không được (xem `SECURITY_PRIVACY.md`).
- JSON mẫu sau thay đổi vẫn qua được validator?

## Mẫu đề xuất
```
Tiêu đề: [contract] <thay đổi ngắn gọn>
Vấn đề:
Trước:
Sau:
Module bị ảnh hưởng:
Tương thích ngược:
Phương án khác:
Cần duyệt: cả nhóm
```
