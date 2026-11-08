# FLOWS.md — Các Luồng Xử Lý Dữ Liệu & Tương Tác Hệ Thống

Tài liệu mô tả chi tiết toàn bộ các luồng dữ liệu (Data Flows), sơ đồ tuần tự (Sequence Diagrams) và cơ chế xử lý lỗi/phục hồi của toàn bộ hệ sinh thái IoT.

---

## 1. Sơ Đồ Kiến Trúc Luồng Dữ Liệu Tổng Thể

```mermaid
flowchart TD
    subgraph HW ["1. Tầng Thu Nhận (firmware/)"]
        CAM["Cảm biến OV2640<br/>(Quét 20MHz)"] --> DMA["Bộ đệm kép PSRAM<br/>(fb_count = 2)"]
        DMA --> HTTP_SRV["HTTP Stream Server<br/>(Endpoint: /stream)"]
    end

    subgraph AI ["2. Tầng Trí Tuệ Nhân Tạo (vision/)"]
        HTTP_SRV -- "MJPEG Stream (HTTP/LAN)" --> CAP["VideoCaptureStream<br/>(Bufferless Reader)"]
        CAP --> YOLO["YOLOv8 Pose<br/>(Inference 17 Keypoints)"]
        YOLO --> ANG["Tính góc Trunk Angle<br/>(Vector Vai-Hông / Vai-Tai)"]
        ANG --> CLF["Classifier & Smoothing<br/>(Cửa sổ làm mượt N frames)"]
        CLF --> PUB["MQTT Publisher<br/>(Paho Client)"]
    end

    subgraph BRK ["3. Tầng Trung Chuyển"]
        PUB -- "JSON Event (QoS 1)<br/>Topic: classroom/posture/events" --> MOSQ[("MQTT Broker<br/>Eclipse Mosquitto")]
    end

    subgraph BE ["4. Tầng Lưu Trữ & Xử Lý (backend/)"]
        MOSQ --> SUB["MQTT Subscriber"]
        SUB --> VAL{"Validator Schema<br/>(Đủ 7 trường?)"}
        VAL -- "Sai schema" --> REJ["Log cảnh báo & Bỏ qua"]
        VAL -- "Hợp lệ" --> DEDUP{"Check event_id<br/>(Đã tồn tại?)"}
        DEDUP -- "Trùng" --> IGN["Bỏ qua (Deduplicated)"]
        DEDUP -- "Mới" --> DB[("SQLite Database<br/>posture_events")]
        DB --> API["FastAPI REST Service<br/>(/api/events/latest)"]
    end

    subgraph FE ["5. Tầng Trực Quan Hóa (web/)"]
        API -- "JSON Response (Polling 2s)" --> DASH["Web Dashboard<br/>(Render Thẻ ghế & Lịch sử)"]
        HTTP_SRV -. "Xem trực tiếp (Tùy chọn)" .-> DASH
    end
```

---

## 2. Chi Tiết Các Luồng Nghiệp Vụ Cụ Thể

### Luồng 1: Thu nhận và phát luồng video (`firmware/`)
1. ESP32-CAM khởi động, nạp cấu hình Wi-Fi từ `secrets.h`.
2. Can thiệp thanh ghi `RTC_CNTL_BROWN_OUT_REG` để vô hiệu hóa ngắt sụt áp khi phát sóng Wi-Fi công suất cao.
3. Kích hoạt PSRAM để cấp phát 2 bộ đệm khung hình DMA (`fb_count = 2`) với xung nhịp 20MHz.
4. Mở Server HTTP lắng nghe kết nối tại cổng mặc định; khi có client kết nối tới `/stream`, thiết bị truyền liên tục các frame JPEG theo định dạng `multipart/x-mixed-replace`.

### Luồng 2: Xử lý thị giác máy tính & Phân loại tư thế (`vision/`)
```mermaid
sequenceDiagram
    autonumber
    actor Cam as ESP32-CAM (/stream)
    participant Cap as capture.py
    participant Pose as pose_estimator.py
    participant Ang as angle.py
    participant Clf as classifier.py
    participant Pub as mqtt_publisher.py

    Cap->>Cam: Kết nối đọc luồng HTTP
    Cam-->>Cap: Trả về frame JPEG liên tục
    loop Mỗi chu kỳ khung hình
        Cap->>Pose: Gửi frame BGR (đã xoay 180° nếu cần)
        Pose->>Pose: Suy luận YOLOv8 Pose (trích 17 điểm)
        Pose-->>Ang: Danh sách keypoints + confidences
        Ang->>Ang: Tính góc thân so với phương thẳng đứng
        Ang-->>Clf: Giá trị góc (độ)
        Clf->>Clf: Gán nhãn thô & Bỏ vào cửa sổ làm mượt (5 frames)
        Clf-->>Pub: Nhãn đã làm mượt (upright/slouching/leaning)
        alt Đủ chu kỳ gửi (1s) hoặc nhãn thay đổi
            Pub->>Pub: Đóng gói JSON kèm event_id, UTC, seat_id
            Pub->>Pub: Phát bản tin lên MQTT Broker (QoS 1)
        end
    end
```

### Luồng 3: Tiếp nhận, xác thực và lưu trữ (`backend/`)
1. `mqtt_subscriber.py` nhận bản tin nhị phân từ topic `classroom/posture/events`.
2. Chuyển sang `validator.py`:
   - Kiểm tra định dạng JSON hợp lệ.
   - Kiểm tra bắt buộc có đủ 6 trường: `event_id`, `ts`, `seat_id`, `label`, `confidence`, `model`.
   - Kiểm tra `label` nằm trong tập hợp hợp lệ `{"upright", "slouching", "leaning", "unknown"}`.
   - Kiểm tra `confidence` nằm trong khoảng $[0.0, 1.0]$.
3. Nếu hợp lệ, gọi hàm `insert_event()` trong `database.py`:
   - Thực thi `INSERT OR IGNORE INTO posture_events ...`.
   - Nếu `event_id` đã có trong CSDL, câu lệnh tự động bỏ qua (loại bỏ lặp do QoS 1).

### Luồng 4: Hiển thị trực quan trên Web Dashboard (`web/`)
1. Client tải trang `index.html`.
2. Trình duyệt tự động kích hoạt vòng lặp polling mỗi 2 giây:
   - Gửi yêu cầu `GET /api/events/latest`.
   - Nhận danh sách trạng thái mới nhất của các ghế.
   - Cập nhật màu sắc thẻ ghế và thông số góc trên giao diện DOM.
3. Đồng thời mỗi 5 giây, gửi yêu cầu `GET /api/events?limit=20` để cập nhật bảng lịch sử sự kiện.
4. Gửi yêu cầu `GET /api/health` để cập nhật tình trạng sống của Broker và Backend.

---

## 3. Luồng Xử Lý Sự Cố & Tự Phục Hồi (Fault Tolerance Flows)

```mermaid
flowchart TD
    E1["Mất kết nối Camera Stream<br/>(ESP32-CAM mất Wi-Fi/nguồn)"] --> R1["capture.py bắt lỗi đọc frame<br/>Sleep 0.5s -> Tự gọi _connect() thử lại"]
    R1 --> S1["Gửi nhãn 'unknown' với confidence 0.0 lên MQTT"]

    E2["Mất kết nối MQTT Broker<br/>(Broker khởi động lại)"] --> R2["Paho MQTT tự động kích hoạt callback on_disconnect()<br/>Thực hiện reconnect_async ngầm"]
    R2 --> S2["Khi Broker online, tự resubscribe topic mà không cần restart service"]

    E3["Bản tin MQTT sai cấu trúc / Lạ trường"] --> R3["validator.py phát hiện thiếu trường / sai kiểu"]
    R3 --> S3["Ghi log cảnh báo và drop bản tin, không ghi vào CSDL"]
```
