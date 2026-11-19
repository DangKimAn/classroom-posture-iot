# Benchmark hiệu năng backend (B3)

Tài liệu này chuẩn bị cách chạy B3 trên một database PostgreSQL disposable. **Benchmark chưa được chạy trong lượt chuẩn bị này; không có số liệu nào được tạo.** Script không tải `.env`; chỉ dùng các biến môi trường của process hiện tại.

## Đo những gì

- Seed mặc định 1.000.000 event tổng hợp cho 40 `seat_id` có tiền tố `TEST-`, timestamp trải trên 7 ngày.
- Chạy `ANALYZE posture_events` sau bulk seed để planner có thống kê cập nhật trước khi đo query.
- Đo p50/p95/mean của `latest_events` và `query_events` (mặc định 50 lần mỗi truy vấn).
- Chạy `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` cho truy vấn latest và history tương ứng.
- So sánh ingest mở connection mỗi event với tái sử dụng một connection, ở 10/40/100 event mỗi giây. Mặc định mỗi mức chạy 100 event cho từng chế độ; mỗi event đều commit riêng.
- Xóa các dòng của lượt chạy theo `model_version` ngẫu nhiên và seat ID `TEST-BENCH-*` trong `finally`. Database phải rỗng trước khi seed. Container PostgreSQL disposable trong runbook cũng bị xóa khi kết thúc.

JSON kết quả chỉ được tạo sau khi cleanup thành công, trong `reports/perf_backend/backend-benchmark-<run_id>.json`. File chứa cấu hình, môi trường, thời gian đo, query plans và số dòng đã xóa; không chứa DSN, username hay password. Không tạo file kết quả mẫu vì chưa có phép đo thật.

## Guard an toàn

Để script bắt đầu, tất cả điều kiện sau phải đạt:

1. Database name lấy từ `DB_NAME` hoặc tên ghi rõ trong `DB_URL` phải bắt đầu bằng `test` (không phân biệt hoa thường).
2. Tên database thực tế từ `SELECT current_database()` phải khớp tên cấu hình.
3. Có cờ `--confirm-disposable-db` **và** biến process `RUN_BACKEND_BENCHMARK=I_CONFIRM_DISPOSABLE_TEST_DB`.
4. Bảng `posture_events` phải rỗng sau khi migration được áp dụng.

Script dừng trước seed nếu guard nào không đạt. Không chạy trên database chính, kể cả khi có thể đổi tên biến môi trường. Không truyền hoặc in credential thật.

## Runbook PowerShell

Chạy từ thư mục gốc repository. Dùng PowerShell mới để tránh biến DB của phiên làm việc khác. Compose dưới đây chỉ khởi động service `postgres` trong `docker-compose.test.yml`; project được đặt tên riêng và file compose không gắn volume dữ liệu.

### 1. Kiểm tra trước khi khởi động

```powershell
docker version
docker compose version
python -m pip install -r backend/requirements.txt
python -m backend.tools.benchmark_backend --help
```

Đảm bảo Docker Desktop đang chạy và host port `15432` chưa được service khác sử dụng. Nếu bận, dừng và xử lý xung đột port trước; không đổi sang project Compose chính.

### 2. Tạo database, chạy benchmark và dọn project

Khối PowerShell dưới đây tạo project có tên ngẫu nhiên, chỉ khởi động service PostgreSQL, tạo database mới, chạy benchmark, khôi phục biến môi trường process và dọn đúng project đó trong `finally`. `DB_URL` được để rỗng để nó không ghi đè target test bằng DSN từ phiên PowerShell.

```powershell
$project = "posture-perf-b3-$([guid]::NewGuid().ToString('N').Substring(0,8))"
$composeArgs = @("-p", $project, "-f", "docker-compose.test.yml")
$names = @("DB_URL", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD", "RUN_BACKEND_BENCHMARK")
$previous = @{}
foreach ($name in $names) {
  $previous[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
}
Write-Host "Disposable Compose project: $project"

try {
  docker compose @composeArgs up -d --wait postgres
  if ($LASTEXITCODE -ne 0) { throw "Disposable PostgreSQL did not become ready." }

  docker compose @composeArgs exec -T postgres psql -U posture_test -d posture_test `
    -v ON_ERROR_STOP=1 -c "CREATE DATABASE test_perf_backend"
  if ($LASTEXITCODE -ne 0) { throw "Could not create the benchmark database." }

  $env:DB_URL = ""
  $env:DB_HOST = "127.0.0.1"
  $env:DB_PORT = "15432"
  $env:DB_NAME = "test_perf_backend"
  $env:DB_USER = "posture_test"
  $env:DB_PASSWORD = "posture_test_only"
  $env:RUN_BACKEND_BENCHMARK = "I_CONFIRM_DISPOSABLE_TEST_DB"

  python -m backend.tools.benchmark_backend --confirm-disposable-db
  if ($LASTEXITCODE -ne 0) { throw "Benchmark stopped; inspect its safe error message." }

  Get-ChildItem reports/perf_backend -Filter "backend-benchmark-*.json"
}
finally {
  foreach ($name in $names) {
    if ($null -eq $previous[$name]) {
      Remove-Item "Env:$name" -ErrorAction SilentlyContinue
    }
    else {
      Set-Item -Path "Env:$name" -Value $previous[$name]
    }
  }
  docker compose @composeArgs down
}
```

Nếu lệnh báo database đã tồn tại hoặc port `15432` bận, `finally` vẫn dọn đúng project vừa tạo. Mật khẩu PostgreSQL là credential test trong `docker-compose.test.yml`, không phải credential stack chính. Không thêm `DB_URL` của stack chính. Script từ chối database không có tiền tố `test`, thiếu một trong hai xác nhận, target thực tế không khớp, hoặc database có sẵn rows.

### 3. Kiểm tra kết quả

Chỉ ghi nhận số liệu nếu script kết thúc mã 0 và tạo JSON kết quả. Kiểm tra trường `cleanup.seed_rows_deleted` bằng số row seed cộng số event ingest. Nếu benchmark bị ngắt, script vẫn cố xóa dòng theo marker; project PostgreSQL disposable cũng bị xóa trong `finally`. Không cộng kết quả này vào báo cáo E2E.

Lệnh `down` chỉ nhắm project name vừa tạo. Không thêm `-v`, không dùng project name của stack chính. Nếu PowerShell bị đóng bất thường trước `finally`, khởi động phiên PowerShell mới và chạy `docker compose -p <project-name-vừa-tạo> -f docker-compose.test.yml down` với đúng project name đã lưu lại.

### Tùy chọn kích thước workload

Các tham số chỉ để giảm workload khi kiểm tra setup trên DB disposable; kết quả đó không thay thế B3 một triệu event:

```powershell
python -m backend.tools.benchmark_backend --confirm-disposable-db `
  --rows 10000 --query-iterations 5 --ingest-events 10 --rates 10 40 100
```

Khi cần kết quả B3, dùng mặc định 1.000.000 rows, 40 seat, 7 ngày, 50 query samples và 100 event ở từng tổ hợp rate/chế độ kết nối. JSON ghi platform, phiên bản Python và số CPU logic; ghi thêm RAM/Docker Desktop resource limit trong ghi chú khi diễn giải kết quả. Không suy rộng số đo từ môi trường khác.
