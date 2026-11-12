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

`latency_ms = received_at - ts`. Chỉ số chỉ có ý nghĩa khi đồng hồ vision và backend được đồng bộ. Event có timestamp tương lai hoặc độ lệch âm cần được loại khỏi thống kê latency và đếm riêng hoặc báo rõ trong metadata. Đây là thời gian từ lúc vision tạo event đến khi backend nhận; không đại diện độ trễ từ lúc camera chụp đến khi dashboard render.

### 2.4 `GET /api/health`

Endpoint mới để báo khả năng phục vụ của backend và kết nối cơ sở dữ liệu. Endpoint này không tự chứng minh pipeline vision hoặc camera đang hoạt động.

### 2.5 Migration

Thêm migration `002_add_received_at.sql`:

```sql
ALTER TABLE posture_events
ADD COLUMN IF NOT EXISTS received_at TIMESTAMPTZ NOT NULL DEFAULT now();
```

Giá trị mặc định hỗ trợ các dòng dữ liệu đã có trước migration. Với dữ liệu cũ, `received_at` là thời điểm áp dụng migration, không phải thời điểm nhận thật; các thống kê độ trễ cũ cần được loại trừ hoặc đánh dấu không xác định.

## 3. Phương án trạng thái pipeline

### Phương án A: Event định kỳ làm heartbeat

TV2 gửi event cho mỗi ghế mỗi 2 giây, kể cả nhãn `unknown`, đồng thời gửi ngay khi nhãn sau làm mượt thay đổi. Dashboard đánh dấu stale sau khoảng 3–5 chu kỳ, tương đương 6–10 giây ở chu kỳ 2 giây.

- **Ưu:** Không thêm topic hoặc schema MQTT; có freshness theo từng ghế; triển khai đơn giản.
- **Nhược:** Tăng lưu lượng, số dòng DB và event lặp; cần bảo đảm publisher thực sự gửi định kỳ.

### Phương án B: Topic trạng thái riêng và Last Will

Thêm topic `classroom/posture/status`, retained, QoS 1 và cấu hình MQTT Last Will. Schema gợi ý:

```json
{
  "source": "vision",
  "state": "online",
  "camera": "connected",
  "ts": "2026-11-10T03:12:45Z",
  "fps": 8.0
}
```

Last Will phát `state: offline` khi broker phát hiện kết nối MQTT bị mất. Cần chốt schema cho trạng thái tắt bình thường, timestamp, ý nghĩa `fps`, chu kỳ heartbeat và trạng thái khi camera mất nhưng tiến trình vision vẫn chạy.

- **Ưu:** Tách trạng thái dịch vụ khỏi event tư thế; có thể phân biệt pipeline offline với trạng thái camera nếu các tín hiệu được định nghĩa rõ.
- **Nhược:** Thêm topic, schema và luồng xử lý cho cả TV2 và TV3; retained status chỉ cho biết giá trị cuối cùng và cần quy tắc phát hiện dữ liệu quá cũ.

### Khuyến nghị để nhóm xem xét

Dùng phương án A làm nền cho freshness theo từng ghế. Chỉ bổ sung phương án B nếu nhóm cần phân biệt rõ camera mất kết nối với tiến trình vision chết. Hai phương án có thể kết hợp, nhưng cần tránh ghi event heartbeat vào lịch sử như event đổi nhãn nếu nhóm muốn giảm dung lượng.

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

1. Chọn phương án A, B hay kết hợp? Nhịp event/heartbeat và ngưỡng stale chính xác là bao nhiêu?
2. Giới hạn khoảng thời gian và số bucket của timeline là bao nhiêu? Bucket minute có đủ cho demo?
3. Event có timestamp tương lai hoặc latency âm được loại, đếm riêng hay trả thêm metadata?
4. `/api/health` chỉ kiểm tra DB hay phải kiểm tra thêm subscriber/broker?
5. Với phương án B, ai là nguồn xác định trạng thái camera; payload Last Will và trạng thái graceful shutdown dùng cùng schema nào?

## 5. Phạm vi và phê duyệt

Tài liệu này chỉ là đề xuất. Không triển khai migration, endpoint, trường response, topic, schema status hoặc code dashboard thuộc Phần B cho đến khi PR hợp đồng được cả ba thành viên duyệt và merge. Sau đó mỗi module cập nhật code trong PR riêng.
