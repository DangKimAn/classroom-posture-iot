---
name: review-pr
description: Checklist review Pull Request cho repo đồ án IoT tư thế ngồi: kiểm tra ranh giới module, tuân thủ hợp đồng dữ liệu, bí mật/quyền riêng tư, khả năng chạy theo README, test và bằng chứng, chất lượng mã và tài liệu. Dùng skill này khi được nhờ review một PR hoặc diff, kiểm tra trước khi merge, hoặc tự rà lại thay đổi của mình trước khi mở PR.
---

# Review một Pull Request

Review tốt trả lời được: "merge cái này có làm `main` hỏng, lộ dữ liệu, hay làm module khác vỡ không?". Ưu tiên theo thứ tự dưới đây; vấn đề ở mục trên chặn merge.

## 1. Chặn merge (blocker)
- **Bí mật/dữ liệu nhạy cảm trong diff:** `.env`, mật khẩu Wi-Fi, khóa broker, video lớp học, ảnh có mặt người, dữ liệu nhận dạng, trọng số lớn. Nếu có: yêu cầu gỡ và báo đổi khóa nếu là bí mật thật.
- **Vi phạm quyền riêng tư:** lưu/gửi ảnh, thêm trường danh tính, log tên/MSSV, diễn giải nhãn như đánh giá sức khỏe/thái độ.
- **Đổi hợp đồng ngầm:** tên topic, trường event, enum, bảng DB, endpoint khác với `DATA_CONTRACT.md` mà không có PR hợp đồng.
- **Sửa ngoài module** của issue mà không có thỏa thuận.
- **Không chạy được** theo README hoặc làm `main` hỏng.

## 2. Cần sửa (should fix)
- Thiếu test/ca biên cho phần thay đổi (keypoint thiếu, bản tin sai schema, `event_id` trùng, mất kết nối).
- Hard-code URL/ngưỡng/mật khẩu thay vì cấu hình.
- Nuốt lỗi im lặng; không có reconnect/retry ở dịch vụ chạy lâu.
- Thời gian không phải UTC; góc không phải độ; thiếu kiểm tra tham số API.
- Tài liệu/README không cập nhật theo thay đổi.
- Tuyên bố số đo/kết quả không có log hoặc điều kiện thử.

## 3. Gợi ý (nit)
Đặt tên, cấu trúc hàm, comment, định dạng theo `CONVENTIONS.md`.

## Cách trả lời review
```
Tóm tắt: <PR làm gì, 1–2 dòng>
Blocker: <danh sách hoặc "không có">
Cần sửa: <danh sách>
Gợi ý: <danh sách>
Đã kiểm: <đã chạy lệnh/test nào, kết quả; phần nào chưa kiểm chứng được>
Kết luận: Approve / Request changes
```

Dẫn đúng file và dòng khi nêu vấn đề. Nêu lý do, không chỉ nói "sai". Khen điều làm tốt khi có. Không approve nếu chưa tự chạy hoặc chưa ghi rõ đã không chạy được vì sao.
