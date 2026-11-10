# Firmware ESP32-CAM HTTP MJPEG Stream

Mã nguồn điều khiển module **AI-Thinker ESP32-CAM (Cảm biến OV2640 2MP)** phục vụ việc thu nhận và phát luồng video MJPEG thời gian thực qua giao thức HTTP trong mạng cục bộ (LAN), cung cấp đầu vào cho khối thị giác máy tính (`vision/`).

Thuộc trách nhiệm của: **Thành viên 1 (TV1 — Thiết bị & Wi-Fi)**.

---

## 1. Sơ Đồ Nối Dây Phần Cứng (Hardware Wiring)

### 1.1. Nối mạch nạp FTDI USB-to-UART để nạp code
ESP32-CAM không tích hợp sẵn chip nạp USB-UART, cần sử dụng mạch nạp ngoài (FTDI / CP2102 / CH340).

```text
  [Mạch Nạp FTDI]            [ESP32-CAM AI-Thinker]
  VCC (Set Jumper 5V) ------> 5V  (KHÔNG dùng chân 3V3 vì dễ sụt áp)
  GND ----------------------> GND
  TXD ----------------------> U0R (GPIO 3)
  RXD ----------------------> U0T (GPIO 1)
                              IO0 <---> GND (NỐI TẮT khi nạp code, THÁO RA khi chạy)
```

> [!IMPORTANT]
> - **Khi nạp code**: Nối chân `IO0` xuống `GND`, sau đó nhấn nút `RST` một lần để đưa chip vào chế độ Download Bootloader.
> - **Sau khi nạp xong**: **Rút dây nối `IO0` khỏi `GND`**, sau đó nhấn nút `RST` một lần nữa để ESP32-CAM khởi động vào chế độ chạy bình thường.

### 1.2. Lưu ý về nguồn cấp chống sụt áp (Brownout Prevention)
Khi ESP32-CAM phát Wi-Fi và truyền video, dòng điện tiêu thụ có thể đạt đỉnh **350–500mA**. Nếu nguồn USB máy tính yếu hoặc dây cáp kém chất lượng, vi điều khiển sẽ bị sập nguồn liên tục.
* Khuyến nghị dùng nguồn cắm ngoài **5V - 2A** độc lập.
* Nếu bị reset ngẫu nhiên, hàn thêm một tụ hóa **$100\mu\text{F} - 470\mu\text{F}$** (10V–16V) song song giữa chân `5V` và `GND` của ESP32-CAM để san phẳng dòng đỉnh.
* Firmware đã được tích hợp lệnh vô hiệu hóa thanh ghi `RTC_CNTL_BROWN_OUT_REG` để ngăn kích hoạt ngắt bảo vệ brownout.

---

## 2. Cài Đặt Môi Trường & Cấu Hình Nạp Code

### 2.1. Cấu hình trên Arduino IDE
1. Cài đặt ESP32 Board Package (phiên bản `>= 2.0.14` hoặc `3.x`):
   * URL thêm vào Board Manager: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
2. Chọn Board: **Tools > Board > ESP32 Arduino > AI Thinker ESP32-CAM**.
3. Cấu hình thông số nạp (Tools):
   * **CPU Frequency**: `240MHz (WiFi/BT)`
   * **Flash Frequency**: `80MHz`
   * **Flash Mode**: `QIO`
   * **Partition Scheme**: `Huge APP (3MB No OTA/1MB SPIFFS)` *(Bắt buộc để đủ dung lượng)*
   * **PSRAM**: `Enabled` *(Bắt buộc để kích hoạt bộ nhớ ngoài 4MB và DMA kép)*
   * **Upload Speed**: `115200` (hoặc `460800` nếu mạch nạp ổn định)

### 2.3. Cấu hình vận hành tiêu chuẩn (Standard Operating Point)
Hệ thống sử dụng cấu hình cân bằng tối ưu ("Goldilocks Configuration"):
* **Độ phân giải chuẩn**: **QVGA ($320\times240$, tỉ lệ 4:3)** — khung hình to rõ, diện tích hiển thị gấp 3 lần so với QCIF, đảm bảo mô hình YOLOv8 Pose nhận diện chính xác các khớp vai, tai, hông của sinh viên.
* **Tốc độ khung hình**: **$8 - 10\text{ FPS}$ cố định** ($100\text{ms}$/frame) với bộ điều tốc (Frame Pacer), không giật lag.
* **Chất lượng nén JPEG**: Mức **60**, cân bằng hoàn hảo giữa độ nét và thời gian nén của CPU.
* **Tự động thích ứng phần cứng**: Tự động nhận diện cảm biến OV2640 (Hardware JPEG VGA 20-25 FPS) hoặc OV7670 (Optimized Software JPEG QVGA 8-10 FPS).

### 2.4. Thiết lập thông tin Wi-Fi bí mật (`secrets.h`)
Theo quy chuẩn bảo mật `SECURITY_PRIVACY.md`, tuyệt đối không commit thông tin Wi-Fi lên Git.
1. Sao chép file mẫu:
   ```bash
   cp secrets.example.h secrets.h
   ```
2. Mở file `secrets.h` và điền tên Wi-Fi + mật khẩu:
   ```c
   const char* WIFI_SSID = "WiFi_Phong_Hoc";
   const char* WIFI_PASS = "MatKhau123";
   ```
*(File `secrets.h` đã được khai báo trong `.gitignore` nên an toàn không bị commit nhầm).*

---

## 3. Vận Hành & Kiểm Tra Luồng (Verification)

1. Mở **Serial Monitor** với tốc độ **115200 baud**.
2. Nhấn nút `RST` trên ESP32-CAM.
3. Quan sát log khởi động:
   ```text
   ========================================================
     Classroom Posture Monitor — ESP32-CAM Video Streamer  
   ========================================================
   [CAM] PSRAM 4MB found. Enabling VGA (640x480) Double Buffer DMA.
   [CAM] Camera initialized successfully
   [WiFi] Connecting to SSID: WiFi_Phong_Hoc
   ......
   [WiFi] Connected successfully!
   [WiFi] IP Address: http://192.168.1.105
   [WiFi] Stream URL: http://192.168.1.105/stream
   [WiFi] RSSI Signal: -55 dBm
   [HTTP] Starting web server on port: '80'
   [HTTP] Camera stream server started successfully
   [SYSTEM] Ready. Waiting for AI Vision client connection...
   ```
4. **Kiểm tra đường dẫn (Endpoints):**
   * **Xem luồng trực tiếp**: Mở trình duyệt web hoặc VLC Player tại:
     `http://192.168.1.105/stream`
   * **Xem thông số thiết bị**: Mở:
     `http://192.168.1.105/status` (trả về JSON trạng thái, FPS, RAM, RSSI).
5. **Cung cấp cho Thành viên 2 (Vision):**
   * TV1 bàn giao đường dẫn luồng này cho TV2 cấu hình vào file `.env`:
     ```env
     CAM_STREAM_URL=http://192.168.1.105/stream
     ```

---

## 4. Xử Lý Sự Cố Thường Gặp (Troubleshooting)

| Hiện tượng | Nguyên nhân | Giải pháp |
| :--- | :--- | :--- |
| `Camera init failed with error 0x20001` | Cáp dải ruy-băng camera OV2640 bị lỏng hoặc cắm ngược chân | Tháo lẫy giữ cáp camera, cắm chặt lại cáp dẹp sao cho mặt chân tiếp xúc hướng đúng chiều, khóa lẫy. |
| `Brownout detector was triggered` / Reset liên tục | Nguồn cấp 5V không đủ dòng khi bật phát sóng Wi-Fi | Dùng củ sạc 5V-2A xịn; không dùng cổng USB máy tính yếu; gắn thêm tụ bù 100uF giữa 5V và GND. |
| `Timed out waiting for packet header` khi nạp | Chưa nối IO0 với GND hoặc mạch nạp chưa bắt tín hiệu | Kiểm tra dây nối `IO0` về `GND`, nhấn nút `RST` ngay khi Arduino IDE hiện chữ `Connecting........_____.....` |
| Video bị giật, trễ tích lũy hàng chục giây | Bên nhận (OpenCV) dùng hàng đợi frame mặc định | TV2 cần sử dụng lớp đọc đa luồng không đệm (Bufferless) đã cung cấp trong `vision/`. |
| Wi-Fi mất kết nối giữa chừng | Sóng yếu hoặc router khởi động lại | Firmware tự động kích hoạt `WiFi.reconnect()` mỗi 5 giây cho đến khi có mạng trở lại. |

---

## 5. Quy Trình Đo Đạc Số Liệu Phục Vụ Báo Cáo

Theo `TESTING.md`, TV1 cần thực hiện các phép đo sau trên phần cứng thật để đưa số liệu vào Chương 3 của báo cáo:

### 5.1. Đo tốc độ khung hình (FPS) trực tiếp trên ESP32-CAM
Firmware đã tích hợp 2 cơ chế tự đo FPS:
1. **Đo phần cứng thuần lúc khởi động (Raw Hardware Benchmark)**:
   * Khi khởi động, hàm `benchmarkSensorFPS(30)` tự động chụp 30 khung hình liên tiếp trực tiếp từ cảm biến OV2640 (không qua Wi-Fi) và in ra Serial:
     ```text
     [BENCHMARK] Raw Hardware FPS  : 26.80 FPS
     [BENCHMARK] Avg JPEG Size     : 22.4 KB per frame
     [BENCHMARK] Data Throughput   : 4.80 Mbps
     ```
2. **Đo tốc độ stream qua mạng (Streaming Telemetry)**:
   * Khi có client kết nối xem `/stream`, Serial Monitor sẽ in thông số thực thời mỗi 2 giây:
     ```text
     [TELEMETRY] Streaming FPS: 24.2 | Wi-Fi RSSI: -54 dBm | Free PSRAM: 3840 KB
     ```
   * Hoặc truy cập trực tiếp `http://<IP_ESP32>/status` để lấy JSON metrics.

### 5.2. Đo tốc độ khung hình & độ trễ mạng từ máy tính (Client-side Benchmark)
Để có số liệu khách quan từ phía máy tính nhận luồng (OpenCV/Python), sử dụng công cụ đo chuyên dụng:
```bash
# Đo hiệu năng stream từ ESP32-CAM trong 10 giây:
python3 tests/mocks/camera_fps_benchmark.py --url http://192.168.1.xxx/stream --duration 10
```
Script sẽ xuất ra bảng phân tích chi tiết:
* **Average, Peak & Min FPS**.
* **Độ trễ trung bình giữa 2 frame (Frame interval)** và **Độ biến thiên giật lag (Jitter)**.
* **Số khung hình bị trễ/nghẽn (Lagged/stalled frames)**.
* **Băng thông mạng thực tế (Mbps)** và **Kích thước trung bình mỗi frame JPEG (KB)**.

### 5.3. Đo độ trễ truyền mạng LAN
Dùng máy tính cùng mạng chạy lệnh ping `ping <IP_ESP32>` liên tục 100 gói để ghi nhận $RTT_{\text{avg}}$ (tiêu chuẩn: $<30\text{ms}$).

