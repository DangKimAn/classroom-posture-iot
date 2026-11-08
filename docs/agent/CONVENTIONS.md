# Quy chuẩn viết mã và tài liệu

Mục tiêu: người/agent khác đọc, chạy và review được mà không cần hỏi lại tác giả.

## Chung
- Mã, tên biến/hàm/file, log, commit, tên nhánh: tiếng Anh. Tài liệu `docs/` và báo cáo: tiếng Việt.
- Không hard-code URL, ngưỡng, topic, mật khẩu; dùng biến môi trường hoặc file cấu hình.
- Thời gian: UTC, ISO-8601. Góc: độ. Mã vị trí: `seat_id`.
- Mỗi module có `README.md` ghi: mục đích, cài đặt, cấu hình, lệnh chạy, lệnh test, giới hạn.
- Hàm nhỏ, có tên mô tả; tách phần logic thuần khỏi I/O để test được.
- Xử lý lỗi rõ ràng: không nuốt lỗi im lặng; log đủ để biết nguyên nhân; dịch vụ dài hạn phải tự nối lại (camera, broker).
- Log không chứa bí mật, danh tính hay dữ liệu thô nhạy cảm.
- Phụ thuộc: cố định phiên bản (`requirements.txt`/lockfile). Không thêm thư viện nặng khi chưa cần; ghi lý do vào PR nếu thêm.

## Python (`vision/`, và `backend/` nếu dùng Python)
- Tuân thủ PEP 8; type hints cho hàm công khai; docstring ngắn nêu đầu vào/ra và đơn vị.
- Cấu hình ngưỡng ở `config.yaml`, đọc qua một hàm load có kiểm tra.
- Test bằng `pytest`; tên file `test_*.py`.

## TypeScript/JS (`web/`, và `backend/` nếu dùng Node)
- Bật strict mode nếu dùng TypeScript; không dùng `any` khi có thể tránh.
- Gọi API qua một lớp client duy nhất; không rải URL khắp nơi.

## C/C++ Arduino (`firmware/`)
- Bí mật Wi-Fi trong `secrets.h` (gitignore) kèm `secrets.example.h` (giá trị giả).
- Mọi trạng thái lỗi quan trọng in ra Serial có thể đọc.

## Cấu hình và bí mật
`.env` gitignore; `.env.example` chỉ tên biến và giá trị giả. Nếu lỡ commit bí mật thật: coi như đã lộ, báo con người, đổi khóa trước, dọn lịch sử sau.

## Đặt tên
- Nhánh: `feature/<module>-<mô-tả>-#<issue>` (ví dụ `feature/vision-mqtt-publisher-#12`). Module: `firmware | vision | backend | web | docs`.
- Commit: `<type>(<module>): <mô tả ngắn> #<issue>`; type: `feat | fix | docs | test | refactor | chore`.
- File tài liệu: `snake_case.md`; sơ đồ/ảnh để trong `docs/` hoặc `docs/img/`.

## Tài liệu
- Viết ngắn, có ví dụ lệnh chạy được, ghi rõ điều kiện (phiên bản, môi trường).
- Số liệu luôn đi kèm điều kiện thử và nguồn (file/log).
- Không tuyên bố quá mức; nêu giới hạn đã biết.

## Dữ liệu mẫu và test
Dữ liệu giả hoặc đã ẩn danh. Không commit video lớp học, ảnh có mặt người, trọng số lớn khi chưa được thống nhất.
