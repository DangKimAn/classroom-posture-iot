# Kiến trúc

```
[ESP32-CAM] --MJPEG/HTTP/Wi-Fi--> [vision: OpenCV + YOLOv8 Pose + classifier]
[vision] --MQTT JSON (không ảnh)--> [broker] --> [backend subscriber + validator] --> [CSDL]
[CSDL] --> [REST API] --> [web dashboard]
```

## Thành phần và trách nhiệm

| Thành phần | Nhận vào | Phát ra | Không được làm |
| --- | --- | --- | --- |
| `firmware/` (ESP32-CAM) | — | Luồng MJPEG HTTP | Xử lý AI, gửi MQTT, lưu video |
| `vision/` | Luồng MJPEG (`CAM_STREAM_URL`) hoặc video mẫu | Event JSON lên MQTT | Ghi video thô mặc định, gửi ảnh, chứa danh tính |
| Broker | Event | Event tới subscriber | — |
| `backend/` | Event MQTT | Bản ghi DB, REST API | Chấp nhận event sai schema, tự đổi schema |
| `web/` | REST API | Giao diện | Truy cập CSDL trực tiếp |

## Cấu trúc repo
```
firmware/  vision/  backend/  web/  docs/  tests/
.env.example  docker-compose.yml  README.md  AGENTS.md  CLAUDE.md
```

## Ràng buộc thiết kế và lý do
- **Tách theo hợp đồng:** để từng khối phát triển và test độc lập bằng mock, ghép muộn không vỡ.
- **Event nhỏ, không ảnh:** giảm băng thông, giảm rủi ro riêng tư.
- **Tách đọc/suy luận/vẽ trong `vision/`:** để logic góc và phân loại test được không cần camera/GPU.
- **Tách nhận/kiểm tra/lưu trong `backend/`:** để test validator mà không cần broker.
- **Cấu hình qua biến môi trường/config:** không hard-code URL, ngưỡng, bí mật.
- **Hạn chế đã biết:** góc tính trên ảnh 2D chỉ xấp xỉ; hông có thể bị bàn che; ESP32-CAM thường chỉ phục vụ ổn định một client stream.
