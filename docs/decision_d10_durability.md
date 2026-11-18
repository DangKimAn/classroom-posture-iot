# D-10 — Độ bền hàng đợi MQTT khi broker dừng đột ngột

## Cấu hình đã đối chiếu

| Thuộc tính | Stack chính (`mosquitto.conf`) | Broker test P2 (`docker/mosquitto-test-auth.conf`) |
| --- | --- | --- |
| `persistence` | `true` | `true` |
| `persistence_location` | `/mosquitto/data/` | `/mosquitto/data/` |
| `autosave_interval` | `30` giây | `30` giây |
| `max_queued_messages` | `10000` | `10000` |
| `password_file` | `/mosquitto/data/password_file` | `/tmp/passwd` |
| Volume | `mosquitto_data` của stack chính | Volume riêng của project test |

Hai cấu hình có cùng thiết lập persistence, khoảng autosave và giới hạn hàng đợi; file mật khẩu và vòng đời volume khác nhau. P2 dùng broker test cô lập, do đó kết quả P2 chưa phải phép hard-kill trên stack chính.

Theo [tài liệu cấu hình Mosquitto](https://mosquitto.org/man/mosquitto-conf-5.html), `autosave_interval` mặc định là **1800 giây (30 phút)** khi không cấu hình. Cả hai file trên đều ghi đè thành 30 giây. Tài liệu nói `autosave_on_changes` bật chế độ đếm thay đổi thay vì diễn giải khoảng này là giây; hai cấu hình đang xét không khai báo tùy chọn đó. Vì vậy không lấy mặc định 1800 giây làm khoảng thực tế của các broker này.

## Bằng chứng hiện có và giới hạn

- P2: subscriber đã dừng, publisher nhận hoàn tất QoS 1, broker test bị hard-kill trước autosave; DB nhận **0/5** event sau khi broker và subscriber chạy lại.
- P3: cùng dạng thử nghiệm nhưng hard-kill sau autosave; DB nhận **5/5** event.
- P1/P4/P5 đánh giá lần lượt restart bình thường, giữ volume qua down/up và xóa volume test. Chúng không chứng minh rằng broker chính đã được hard-kill thành công trong stack chính.
- Lần chạy ma trận cô lập ngày **2026-11-18** dùng cấu hình broker sao chép từ stack chính, DB/volume dùng một lần, và subscriber thật từ source hiện tại. Kết quả:

  | `autosave_interval` | Subscriber | DB sau hard-kill | Thời gian publish |
  | ---: | --- | ---: | ---: |
  | 1 giây | offline | 5/5 | 0.022 giây |
  | 1 giây | online | 5/5 | 0.163 giây |
  | 5 giây | offline | 5/5 | 0.031 giây |
  | 5 giây | online | 5/5 | 0.016 giây |
  | 30 giây | offline | 0/5 | 0.030 giây |
  | 30 giây | online | 5/5 | 0.006 giây |

  Kết quả 30 giây nằm tại `reports/durability_matrix/results-20261117T173330Z-ffe73c.json`; ID trước publish nằm tại `reports/durability_matrix/event-ids-20261117T173330Z-ffe73c.jsonl`. Lần chạy trước đó ghi bốn kết quả 1/5 giây tại `reports/durability_matrix/results-20261117T172417Z-949895.json`.
- Sáu kết quả trên là của stack cô lập với cấu hình broker chính được sao chép; chúng không dùng volume/DB của stack chính. Thời gian publish chỉ đo quá trình publish và chờ PUBACK, không đo chính xác thời gian từ PUBACK đến lúc lệnh hard-kill hoàn tất.
- Subscriber hiện dùng `client_id` cố định `posture-backend`, `clean_session=False`, nhận QoS 1 và ACK thủ công sau xử lý DB. Cấu hình này hỗ trợ session bền, nhưng không làm dữ liệu trong RAM của broker trở thành dữ liệu đã autosave.

Trong phép thử cô lập với khoảng 30 giây, cả năm event dành cho subscriber offline đều mất sau hard-kill; subscriber online phục hồi đủ 5/5. Ở khoảng 1 và 5 giây, cả hai trạng thái subscriber đều phục hồi đủ 5/5 trong lần chạy ghi nhận. Đây là kết quả của từng thời điểm thử, không chứng minh subscriber online luôn tránh mất dữ liệu hoặc mọi hard-kill subscriber offline đều làm mất dữ liệu. P2 trên broker test trước đó cũng ghi nhận 0/5 trong kịch bản subscriber offline. PUBACK xác nhận broker nhận publish theo giao thức, không chứng minh bản persistence đã được ghi bền xuống đĩa.

## Script kiểm chứng

`backend/tools/run_durability_matrix.py` tạo Compose project, PostgreSQL DB và volume broker riêng cho từng cặp khoảng autosave/kịch bản. Script lấy `mosquitto.conf` làm nguồn, ghi cấu hình broker tạm và chỉ thay `autosave_interval`. Nó chạy cả kịch bản subscriber offline và subscriber online, dùng sự kiện tổng hợp `TEST-*`, ghi event ID vào JSONL và flush xuống đĩa trước khi publish, sau đó đếm các ID trong DB dùng một lần. Trước `docker kill` và dọn volume, script kiểm tra nhãn project/service của tài nguyên đích.

Khoảng mặc định để so sánh là 1, 5 và 30 giây; có thể truyền khoảng khác. Mỗi kịch bản tạo project và volume mới để không trộn kết quả. Script build subscriber từ source hiện tại, áp dụng migration qua entry point hiện có và không khởi động API/dashboard. Không sử dụng `.env` của stack chính.

Lệnh chạy sau khi Docker Engine sẵn sàng và người vận hành xác nhận Docker context là môi trường disposable:

```powershell
python backend/tools/run_durability_matrix.py --confirm-disposable --intervals 1 5 30 --events 5
```

**Trạng thái: ma trận 1/5/30 giây đã chạy đủ sáu ca.** Lần chạy 30 giây hoàn tất sau khi sửa lỗi tên project. Đây là kiểm chứng trên stack cô lập mô phỏng cấu hình broker chính, không phải hard-kill volume/DB chính. Không cộng các kết quả này vào tổng E2E lịch sử.

## Phương án để nhóm cân nhắc

| Phương án | Lợi ích | Chi phí và giới hạn |
| --- | --- | --- |
| Chấp nhận khoảng hiện tại và ghi rõ giới hạn | Không đổi vận hành; đơn giản, không thêm tải ghi | Chấp nhận cửa sổ mất các message chưa autosave khi broker chết; cần xác định giới hạn mất dữ liệu phù hợp cho demo/sản phẩm |
| Rút ngắn `autosave_interval` | Thu hẹp khoảng giữa các lần ghi persistence | Tăng tần suất ghi toàn bộ dữ liệu persistence và tải I/O; không đảm bảo chống mất dữ liệu khi kill xảy ra trước lần ghi tiếp theo; cần đo trên volume và phần cứng đích |
| Thêm durable outbox/đệm phía Vision | Có thể phát lại event chưa được xác nhận bởi luồng ứng dụng, giảm phụ thuộc vào persistence broker | Cần thay đổi module Vision và quy trình phát/đánh dấu/xóa event, quản lý dung lượng và dữ liệu tồn; có thể tạo duplicate nên cần dựa vào `event_id`/idempotency; phải được chủ Vision và nhóm duyệt vì D-10 đang OPEN |

## Khuyến nghị và câu hỏi cần chốt

**Khuyến nghị:** dùng kết quả 30 giây offline 0/5 làm bằng chứng rủi ro cần nhóm cân nhắc; chưa tự hạ khoảng autosave production. Nếu mức mất dữ liệu này không chấp nhận được, nhóm nên chốt ngưỡng và yêu cầu kiểm chứng bổ sung trước khi chọn rút ngắn interval hoặc thêm đệm phía Vision. Đây là khuyến nghị, không phải quyết định thay nhóm; không tự đổi `mosquitto.conf`.

Nhóm cần quyết định:

1. Mức mất event tối đa nào chấp nhận được khi broker bị dừng đột ngột: không cam kết ngoài QoS 1, tối đa một khoảng autosave, hay cần cơ chế phát lại bền phía Vision?
2. Có giữ khoảng 30 giây hiện tại không, hay muốn đánh giá một mục tiêu khác? Nếu thay đổi, ngưỡng I/O/tài nguyên nào được chấp nhận?
3. Có yêu cầu thêm durable outbox phía Vision không? Ai sở hữu thay đổi, giới hạn dung lượng/thời gian lưu là bao nhiêu, và cơ chế xác nhận/xóa bản ghi sẽ dựa vào đâu?
4. Có yêu cầu chạy hard-kill trên stack chính sau khi dựng project/DB/volume dùng một lần và kiểm tra cô lập được xác nhận không?

D-10 vẫn **OPEN**. Tài liệu này không sửa cấu hình broker chính và không chốt lựa chọn thay nhóm.
