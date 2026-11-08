# Hợp đồng dữ liệu (nguồn sự thật cho agent)

Trạng thái: **đề xuất cho tới khi được merge thành `docs/data_contract.md` và `docs/api_contract.md` trong repo** (mốc A, tuần 1). Khi file thật tồn tại, file thật thắng file này; nếu hai nơi lệch nhau, dừng và báo.
Chỉ đổi qua skill `change-contract`.

## 1. Camera → Vision
- ESP32-CAM phát MJPEG qua HTTP trong mạng thử nghiệm.
- Vision đọc URL từ biến môi trường `CAM_STREAM_URL`. Không ghi SSID/mật khẩu Wi-Fi trong mã.
- Cổng và đường dẫn cụ thể (ví dụ `/stream`) là mục `OPEN` D-05; ghi vào `docs/stream_contract.md` khi chốt.
- Độ phân giải/FPS chốt theo năng lực thiết bị (D-09).

## 2. Vision → MQTT
- Topic: `classroom/posture/events`
- Payload (một JSON mỗi sự kiện):

```json
{
  "event_id": "uuid",
  "ts": "2026-11-08T03:12:45Z",
  "seat_id": "S01",
  "label": "leaning",
  "angles": {"trunk": 18.4},
  "confidence": 0.91,
  "model": "yolov8n-pose"
}
```

| Trường | Kiểu | Quy tắc |
| --- | --- | --- |
| `event_id` | UUID string | Duy nhất; dùng chống trùng |
| `ts` | string ISO-8601 | **UTC** |
| `seat_id` | string | Mã vị trí, không phải tên/MSSV |
| `label` | string enum | Xem bên dưới (D-01) |
| `angles.trunk` | number | **Độ**; có thể thiếu/null khi `label = unknown` (xác nhận ở D-02) |
| `confidence` | number | Khoảng 0–1 |
| `model` | string | Tên model/phiên bản |

- Enum nhãn đề xuất MVP: `upright | slouching | leaning | unknown` (D-01). Ví dụ gốc dùng `leaning`.
- **Không** gửi ảnh/video/danh tính. Không thêm trường ngoài hợp đồng.
- QoS và retain: chốt trong `docs/data_contract.md`; mặc định đề xuất QoS 1, không retain. Vì QoS 1 có thể giao lặp, backend phải chống trùng.

## 3. MQTT → Backend → CSDL
- Backend xác thực schema; loại bỏ bản tin thiếu trường; lưu `event_id` duy nhất để tránh trùng; log bản tin lỗi (không log dữ liệu nhạy cảm).
- Bảng tối thiểu: `posture_events(id, ts, seat_id, label, trunk_angle, confidence, model_version)`; cần ràng buộc duy nhất cho `event_id` (thêm cột `event_id` hoặc dùng làm khóa; chốt trong `docs/data_contract.md`).
- Chỉ mục gợi ý: theo `ts` và theo `(seat_id, ts)`.
- Không lưu khung hình. Bí mật nằm trong `.env` đã gitignore.

## 4. Backend → Web (REST)
- Tối thiểu: `GET /api/events/latest`, `GET /api/events?from=&to=&seat_id=`.
- Tham số `from/to` là thời gian ISO-8601 UTC; có giới hạn số bản ghi.
- UI chỉ dùng API, không truy cập CSDL.
- Cách cập nhật: polling hoặc WebSocket, chọn một lần (D-06).

## 5. Biến môi trường (chỉ tên biến trong `.env.example`)
`CAM_STREAM_URL`, `MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD`, `MQTT_TOPIC`, `DB_URL`, cùng cấu hình vùng ghế/`seat_id` (trong config của `vision/`). Giá trị thật không vào Git.

## 6. Quy ước chung
Thời gian UTC; góc độ; `seat_id` thay danh tính; trường tên `snake_case`; thay đổi tương thích ngược khi có thể (thêm trường tùy chọn thay vì đổi nghĩa trường cũ).
