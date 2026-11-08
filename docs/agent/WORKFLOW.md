# Quy trình làm việc, quyền sở hữu và Definition of Done

## 1. Nguyên tắc
`main` luôn chạy được. Mọi thay đổi đi qua Pull Request nhỏ. Mỗi việc là một issue có người phụ trách, đầu ra mong đợi, tiêu chí chấp nhận và nhãn module.

## 2. Quyền sở hữu theo module (theo đường dẫn, không theo người)
Người phụ trách của issue quyết định agent làm ở module nào. Agent chỉ sửa trong module của issue.

| Module (nhãn) | Đường dẫn được sửa | Đường dẫn bị cấm khi không có issue riêng |
| --- | --- | --- |
| `firmware` | `firmware/`, test liên quan | `vision/`, `backend/`, `web/` |
| `vision` | `vision/`, test liên quan | `firmware/`, `backend/`, `web/` |
| `backend` | `backend/`, `docker-compose.yml`, test liên quan | `firmware/`, `vision/`, `web/` |
| `web` | `web/`, test liên quan | `firmware/`, `vision/`, `backend/` |
| `docs` | file riêng của chương/mục trong `docs/` | file `docs/` do người khác viết, README chung |
| Hợp đồng chung | `docs/data_contract.md`, `docs/api_contract.md`, `docs/agent/DATA_CONTRACT.md` | Sửa chỉ qua `change-contract` |

README gốc chỉ sửa qua PR do một người điều phối tổng hợp.

## 3. Vòng đời issue
Cột GitHub Projects: Backlog → Ready → In progress → Review → Done. Milestone theo tuần.

1. Nhận issue, xác nhận đầu ra và tiêu chí; nếu phụ thuộc module khác, comment trước khi code.
2. Tạo nhánh từ `main` theo quy ước tên.
3. Làm bản chạy nhỏ nhất; cập nhật README/test cùng module; commit từng bước nhỏ.
4. Mở PR (mẫu bên dưới); tối thiểu một người khác review; chủ module liên quan review API/hợp đồng.
5. Xử lý góp ý, merge vào `main`, kéo `main` về nhánh, chạy lại kiểm tra liên quan, rồi mới đóng issue.

## 4. Mẫu issue
```
## Đầu ra mong đợi
## Tiêu chí chấp nhận
- [ ] ...
## Phụ thuộc module khác
## Module / Tuần / Milestone
```

## 5. Mẫu PR
```
Closes #<issue>
## Thay đổi
## Cách chạy / kiểm thử
## Bằng chứng (log, ảnh đã ẩn danh)
## Ảnh hưởng hợp đồng chung? Có/Không
## Giả định / việc còn lại
```

## 6. Definition of Done (đóng issue khi đủ tất cả)
- [ ] Mã chạy được theo README trên máy sạch.
- [ ] Tiêu chí chấp nhận của issue đạt và có bằng chứng thật (log/test/số đo).
- [ ] Có test hoặc ca kiểm thử cho phần thay đổi (ít nhất các ca biên chính).
- [ ] Không sửa ngoài module; hợp đồng không bị đổi ngầm.
- [ ] Không có secret, dữ liệu nhận dạng, video lớp học, trọng số lớn trong diff.
- [ ] README/tài liệu liên quan đã cập nhật.
- [ ] PR đã được review và góp ý đã xử lý.

## 7. Cân bằng đóng góp
Cuối mỗi tuần mỗi thành viên tự chấm theo giờ thực tế, issue đã đóng, đầu ra chạy được và hỗ trợ tích hợp. Lệch trên 15% thì chuyển một đầu việc độc lập sang tuần kế. Agent không tự phân lại việc giữa các thành viên; chỉ đề xuất nếu được hỏi.
