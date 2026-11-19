-- Phục vụ latest_events: lấy sự kiện mới nhất của từng seat bằng 1 lần tra index/seat.
-- Khớp đúng thứ tự ORDER BY của truy vấn (ts DESC, id DESC), nên không cần sort.
-- Không dùng CONCURRENTLY vì bộ chạy migration có thể bọc trong transaction.
CREATE INDEX IF NOT EXISTS idx_posture_events_seat_ts_id
    ON posture_events (seat_id, ts DESC, id DESC);
