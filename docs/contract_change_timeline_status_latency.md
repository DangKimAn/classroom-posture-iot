# Đề xuất thay đổi hợp đồng: timeline, trạng thái pipeline và độ trễ

**Trạng thái:** Đề xuất để TV1, TV2 và TV3 review. Chưa thay đổi code hoặc hợp đồng hiện hành.

## 1. Vấn đề và lý do

Dashboard hiện hiển thị nhãn mới nhất theo ghế và lịch sử sự kiện. Bản phân công còn yêu cầu biểu đồ diễn biến theo thời gian, chỉ báo pipeline mất kết nối và tab số đo độ trễ. Các chức năng này cần dữ liệu nhận tại backend và API tổng hợp; frontend hiện không thể suy ra chính xác từ tối đa 100 event gần nhất.

## 2. Đề xuất API và cơ sở dữ liệu

Các thay đổi sau chỉ bổ sung trường và endpoint để client cũ tiếp tục hoạt động.

### 2.1 `GET /api/events/latest`

Bổ sung hai trường cho từng ghế:

```json
{
  "received_at": "2026-11-10T03:12:46Z",
  "age_seconds": 1.2
}
```

- `received_at`: thời điểm backend nhận và lưu event, UTC.
- `age_seconds`: số giây từ `received_at` tới thời điểm truy vấn API, tính phía server.
- Cả hai trường là bổ sung; client cũ có thể bỏ qua.

### 2.2 `GET /api/stats/timeline`

Tham số: `from`, `to`, `seat_id` tùy chọn; `bucket=minute` mặc định. Nếu thiếu `from`, lấy một giờ gần nhất. Giới hạn khoảng thời gian và số bucket để tránh truy vấn nặng.

Response đề xuất:

```json
[
  {"bucket": "2026-11-10T03:12:00Z", "label": "upright", "n": 8},
  {"bucket": "2026-11-10T03:12:00Z", "label": "leaning", "n": 2}
]
```

Bucket được căn theo UTC. Nhóm cần chốt giới hạn bucket tối đa và cách xử lý khoảng thời gian lớn hơn giới hạn.

### 2.3 `GET /api/stats/latency`

Tham số: `from`, `to`, `seat_id` tùy chọn. Response đề xuất:

```json
{
  "count": 120,
  "p50_ms": 84.5,
  "p95_ms": 210.0,
  "max_ms": 450.0,
  "events_per_minute": 30.0
}
```

`latency_ms = received_at - ts`. Chỉ số chỉ có ý nghĩa khi đồng hồ Vision và backend được đồng bộ; `ts` lấy từ đồng hồ nguồn nên có thể lệch. Nếu `ts > received_at`, ghi nhận là timestamp tương lai/latency âm, loại khỏi thống kê latency hợp lệ và đếm riêng; không clamp thành 0. Dữ liệu có `received_at = NULL` là dữ liệu cũ không xác định và không đưa vào thống kê. Latency dương vẫn có thể sai do lệch đồng hồ. Chỉ số này không đại diện độ trễ từ lúc camera chụp đến khi dashboard render.

### 2.4 `GET /api/health`

Endpoint mới để báo khả năng phục vụ của backend và kết nối cơ sở dữ liệu. Endpoint này không tự chứng minh pipeline vision hoặc camera đang hoạt động.

### 2.5 Migration

Thêm migration `002_add_received_at.sql`:

```sql
ALTER TABLE posture_events
ADD COLUMN IF NOT EXISTS received_at TIMESTAMPTZ NULL;
```

Không đặt `DEFAULT` và không backfill cột này: mọi dòng đã tồn tại trước migration giữ `received_at = NULL`, nghĩa là thời điểm nhận không xác định. Với event mới, backend ghi `received_at` do PostgreSQL cấp bằng `clock_timestamp()` trong cùng câu lệnh `INSERT`, tại lúc câu lệnh insert chạy sau khi backend nhận MQTT và bắt đầu lưu event. `age_seconds` là `NULL` khi `received_at` là `NULL`; không suy diễn timestamp nhận từ `ts`.

### 2.6 Yêu cầu kiểm chứng và phân biệt trạng thái

- Yêu cầu tương thích: chạy validator trên Python 3.12 với event tổng hợp có timestamp mili-giây, ví dụ `2026-11-17T12:00:00.123Z`. Trên Python 3.14.3, validator chấp nhận timestamp này. Máy kiểm thử không có Python 3.12, nên kết quả trên Python 3.12 **chưa kiểm chứng**.
- “Không có pose” nghĩa là không phát hiện/không gán được pose cho ghế trong frame; theo luồng hiện tại, trường hợp đó không tạo event. `unknown` là nhãn event riêng, dùng khi có pose được gán nhưng góc thân không đo được hoặc phân loại không đủ chắc chắn. Không đồng nhất thiếu event với nhãn `unknown`.
- Dữ liệu cũ có `received_at = NULL` không có tuổi nhận đáng tin cậy. Không dùng `ts` để giả lập thời điểm nhận.

## 3. Phương án trạng thái pipeline

### Phương án A: Event định kỳ theo ghế

TV2 gửi event cho mỗi ghế mỗi 2 giây, kể cả nhãn `unknown`, đồng thời gửi ngay khi nhãn sau làm mượt thay đổi. Dashboard đánh dấu stale sau khoảng 3–5 chu kỳ, tương đương 6–10 giây ở chu kỳ 2 giây.

- **Ưu:** Không thêm topic hoặc schema MQTT; có freshness theo từng ghế.
- **Nhược:** Vision hiện chỉ phát event khi có pose trong vùng ghế. Ghế trống và pipeline dừng vì vậy không tạo event, trông giống nhau. Chỉ dùng A không thể phân biệt phòng trống với pipeline chết. Gửi lặp cũng tăng lưu lượng và số dòng DB.

### Phương án B tối thiểu: Topic trạng thái và Last Will

Thêm topic `classroom/posture/status`, retained, QoS 1 và cấu hình MQTT Last Will. Vision gửi heartbeat online theo chu kỳ cố định; broker gửi trạng thái offline theo Last Will khi kết nối MQTT bị mất. Payload tối thiểu:

```json
{
  "source": "vision",
  "state": "online",
  "ts": "2026-11-10T03:12:45Z"
}
```

Last Will dùng cùng schema với `state: offline`. Đề xuất ban đầu: heartbeat mỗi **5 giây**, pipeline status stale sau **15 giây** mà không có heartbeat. Các giá trị này chỉ để nhóm xem xét, chưa được chốt. Tín hiệu này phản ánh tiến trình Vision kết nối MQTT; nó không tự xác nhận camera đang cấp khung hình.

**Phương án B đầy đủ** có thể bổ sung trạng thái camera, FPS và trạng thái tắt bình thường. Những trường đó cần định nghĩa nguồn đo, ý nghĩa, và xử lý khi tiến trình còn sống nhưng camera mất kết nối. B tối thiểu không khẳng định trạng thái camera; B đầy đủ có thêm thông tin nhưng tăng schema và công việc tích hợp.

### Khuyến nghị để nhóm xem xét

Kết hợp A để xác định freshness từng ghế với B tối thiểu để phân biệt trạng thái phòng không có event mới với Vision không online. Không ghi heartbeat vào `posture_events` như event tư thế. Chỉ mở rộng thành B đầy đủ nếu nhóm cần tín hiệu riêng cho camera/FPS.

### Định nghĩa trạng thái ghế và tỷ lệ tư thế

- **Ghế đang có người (theo tín hiệu hệ thống):** có event mới nhất với `age_seconds <= N` và pipeline status đang online, chưa stale. Đề xuất ban đầu cho `N` là **10 giây**; nhóm cần chốt giá trị này cùng chu kỳ gửi event.
- Event cũ hơn N giây được đánh dấu stale/vắng và không tính vào tổng ghế đang có người hoặc thống kê tư thế hiện tại.
- Tỷ lệ tư thế xấu tính trên ghế đang có người có nhãn xác định: `(slouching + leaning) / (upright + slouching + leaning)`. Nhãn `unknown` không vào mẫu số và phải được báo riêng (số lượng hoặc tỷ lệ unknown) để người xem biết mức thiếu dữ liệu.
- Nếu pipeline stale/offline, trạng thái ghế hiện tại không được diễn giải là phòng trống.

## 4. Tác động, công việc và tiêu chí chấp nhận

| Thành viên | Công việc sau khi hợp đồng được duyệt |
|---|---|
| TV1 | Xác nhận cách phát hiện camera mất kết nối và tín hiệu nào TV1 có thể cung cấp nếu chọn phương án B. |
| TV2 | Chốt nhịp publish, đảm bảo `ts` UTC; nếu chọn B, phát trạng thái online/offline, Last Will và các trường đã thống nhất. |
| TV3 | Thêm migration, lưu `received_at`, API timeline/latency/health, xử lý status topic nếu chọn B, cập nhật dashboard và test. |

Rủi ro gồm tăng lưu lượng/lưu trữ với event định kỳ, sai số do đồng hồ chưa đồng bộ, sai diễn giải freshness khi chỉ gửi khi nhãn đổi, và retained status cũ sau mất kết nối nếu không có thời gian stale phù hợp.

Tiêu chí chấp nhận đề xuất:

- Client cũ vẫn đọc được `/api/events/latest`; trường mới chỉ được thêm.
- Timeline khớp kết quả truy vấn mẫu theo phút, có giới hạn bucket và lọc ghế/thời gian.
- Latency có kiểm thử với đồng hồ đồng bộ và nêu rõ mẫu âm/tương lai được xử lý ra sao.
- Dashboard phân biệt backend/API không khả dụng với pipeline stale; không kết luận camera offline nếu không có tín hiệu tương ứng.
- Migration chạy trên DB mới và DB đã có dữ liệu mà không xóa dữ liệu.

### Câu hỏi nhóm cần chốt

1. Chọn phương án A, B tối thiểu, B đầy đủ hay kết hợp? Chốt N cho event ghế và chu kỳ heartbeat/stale của pipeline là bao nhiêu? Giá trị đề xuất hiện tại: N=10 giây, heartbeat=5 giây, status stale=15 giây.
2. Giới hạn khoảng thời gian và số bucket của timeline là bao nhiêu? Bucket minute có đủ cho demo?
3. Event có timestamp tương lai hoặc latency âm được loại, đếm riêng hay trả thêm metadata?
4. `/api/health` chỉ kiểm tra DB hay phải kiểm tra thêm subscriber/broker?
5. Với phương án B, ai là nguồn xác định trạng thái camera; payload Last Will và trạng thái graceful shutdown dùng cùng schema nào?
6. **D-04 — trạng thái pipeline/occupancy:** chọn chỉ suy ra freshness từ event, thêm topic status/Last Will, hay kết hợp? Mặc định đề xuất trong tài liệu này là kết hợp event theo ghế với status tối thiểu; các ngưỡng đề xuất 10 giây cho event, heartbeat 5 giây và stale 15 giây vẫn cần nhóm duyệt.
7. **D-06 — cập nhật dashboard:** chọn polling hay WebSocket? Mặc định đề xuất là polling; chu kỳ cụ thể cần nhóm chốt.
8. **D-10 — truyền và lưu hàng đợi MQTT:** chốt QoS, retain, persistence và mức mất event tối đa chấp nhận được? Mặc định đề xuất là QoS 1, không retain, persistence bật với autosave 30 giây; phép thử hard kill đã mất 0/5 event trước autosave nên cần nhóm xác nhận cửa sổ rủi ro này trước khi triển khai.

## 5. Phạm vi và phê duyệt

Tài liệu này chỉ là đề xuất. Không triển khai migration, endpoint, trường response, topic, schema status hoặc code dashboard thuộc Phần B cho đến khi PR hợp đồng được cả ba thành viên duyệt và merge. Sau đó mỗi module cập nhật code trong PR riêng.

## Mẫu issue đề xuất hợp đồng

```text
Tiêu đề: [contract] Thêm freshness ghế và trạng thái pipeline cho dashboard
Vấn đề: API hiện không có tuổi event, và khi Vision chỉ phát event theo pose thì ghế trống không phân biệt được với pipeline dừng.
Trước: API latest không có received_at/age_seconds; MQTT chỉ có topic events; dashboard không có tín hiệu pipeline.
Sau: Bổ sung received_at/age_seconds, timeline/latency/health; cân nhắc topic status retained QoS 1 với Last Will và payload tối thiểu source/state/ts. Đề xuất N=10 giây, heartbeat=5 giây, stale=15 giây; các giá trị cần nhóm chốt.
Module bị ảnh hưởng: vision, backend, web.
Tương thích ngược: Trường API được bổ sung; topic status là luồng mới và không đổi payload/topic events hiện hành.
Phương án khác: Chỉ dùng event định kỳ theo ghế; cách này không phân biệt được phòng trống với pipeline chết.
Cần duyệt: cả nhóm (TV1, TV2, TV3); chưa được xem là đã duyệt.
```
