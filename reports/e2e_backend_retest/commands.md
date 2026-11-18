# Lệnh và output kiểm thử

Tất cả lệnh dùng stack test riêng; không gọi compose chính. Không đọc/in `.env`. API và subscriber được tạo trực tiếp từ module trong Python test harness với biến DB/broker tường minh, tránh `load_dotenv`. DSN đã che; password test không được ghi vào báo cáo.

## Lệnh đã chạy

```powershell
docker compose -p posture-test -f docker-compose.test.yml up -d --wait
# DB_URL được đặt trong process, dạng postgresql://***:***@127.0.0.1:15432/***
python reports/e2e_backend_retest/run_checks.py
# Một lượt Python inline riêng chạy lại B7, restart PostgreSQL và xóa chính xác UUID được tạo.
docker compose -p posture-test -f docker-compose.test.yml down
```

Harness chạy API ở `http://127.0.0.1:18000`. Các URL có query `&` được tạo bằng urllib, không qua PowerShell tokenization. Ví dụ URL thực tế được gửi:

`http://127.0.0.1:18000/api/events?from=2026-11-16T07%3A02%3A19.753822Z&to=2026-11-16T07%3A04%3A19.753851Z`

## Hạ tầng và log nguyên văn quan sát được

- Compose: PostgreSQL và broker đều `Healthy`; broker publish host `127.0.0.1:11883->1883/tcp`, PostgreSQL `127.0.0.1:15432->5432/tcp`.
- Broker: `mosquitto version 2.0.22 starting`; `Config loaded from /mosquitto/config/mosquitto-test.conf.`; `Opening ipv4 listen socket on port 1883.`; `Opening ipv6 listen socket on port 1883.`; `mosquitto version 2.0.22 running`.
- Broker không in dòng `Starting in local only mode`. Có cảnh báo lúc entrypoint thử chown mount read-only: `chown: /mosquitto/config/mosquitto-test.conf: Read-only file system`; healthcheck vẫn Healthy.
- Subscriber startup: `[mqtt] ready; subscribed topic=classroom/posture/events; mid=1`.
- MQTT-00 actual payload: `handshake-ok`.
- MQTT duplicate log: `[mqtt] duplicate event ignored`.
- DB outage API log: `[api] request failed: StorageUnavailableError` (không lộ DSN/password).
- B7 sau phục hồi: `[mqtt] event stored` hai lần; event lúc DB dừng có count 1 sau khi DB bật lại; event sentinel sau phục hồi count 1.

## Output theo ca (actual)

| ID | Output thực tế nguyên văn / số đo |
|---|---|
| MQTT-00 | `connect=successful` (publish/subscribe hoàn tất); nhận payload `handshake-ok`. |
| B1 | `row_counts=[1,1,1,1]; latest_status=200; latest_contains_test_seat=true; history_status=200; history_rows=1`. |
| B2 | `first_count=1; after_duplicate=1; log=[mqtt] duplicate event ignored`. |
| B3 | `valid_counts=[1,1]; invalid_null_count=0`. Seat 1 ký tự trong lần này là `T`, nên test đó bị đánh dấu sai phạm vi và không tính là bằng chứng hợp lệ. |
| B4 | 16 input: missing, extra, bad_uuid, timezone_missing, seat_empty, seat_33, label_invalid, conf_1_5, conf_negative, conf_true, conf_string, angle_nan, angle_inf, bad_json, empty, oversize. Mỗi case `count=0`; `wrong_topic_count=0`; `valid_after_invalid_count=1`. |
| B5 | `db_count=50; api_status=200; matching_api_rows=50; api_newest_first=true; elapsed_seconds=2.55`. |
| API-06a | `400 application/json; charset=utf-8` — `{"error": "Invalid query parameters"}`. |
| API-06b/c/d | Mỗi query hợp lệ trả `200 application/json; charset=utf-8`; khoảng from-to chỉ chứa event trong khoảng; from-only/to-only chấp nhận. |
| API-06e | Equal from/to trả `200`; body `[]`. |
| API-06f | Timestamp thiếu timezone trả `400 application/json; charset=utf-8` — `{"error": "Invalid query parameters"}`. |
| API-06g | limit=1 + seat filter trả `200`, một event thuộc `TEST-B1-0`. |
| D1 POST/PUT/PATCH/DELETE | Mỗi method: `405`, `application/json; charset=utf-8`, `Allow: GET`, `{"error": "Method not allowed"}`. |
| D1 unknown path | Mỗi method trên `/api/not-a-route`: `404`, `application/json; charset=utf-8`, `Allow=null`, `{"error": "Not found"}`. |
| D1 GET | `/api/events/latest`: `200 application/json; charset=utf-8`. |
| D2 | DB stop exit `0`; response `503 application/json; charset=utf-8`, body `{"error": "Service temporarily unavailable"}`; elapsed `2.008s`; DB start exit `0`; recovery status `200`. |
| B6 | Broker restart exit `0`; subscribed log `mid=2`; store count `1`; elapsed `3.63s`. |
| B7 | PostgreSQL stop/start exit `0/0`; outage event count sau phục hồi `1`; post-recovery sentinel count `1`; logs sau phục hồi hai dòng `[mqtt] event stored`. Trong lúc DB dừng không thu thấy log retry/disconnect. |
| Cleanup chính | `77` giá trị event_id được xóa/đối chiếu; `remaining_matching_rows=0`. |
| Cleanup B7 cuối | IDs `a4ea2f77-4f86-4723-8f61-6c49a893f09a`, `823f1b77-a38b-4cf6-a5b6-f4912886a455`; `remaining=0`. |
| GUI / screenshots | Không thể mở browser/DevTools/chụp ảnh trong phiên; `screenshots/` không có ảnh, các ca E BLOCKED. |

## Event IDs đã tạo trong harness chính

Danh sách gồm UUID thật, UUID sai `not-a-uuid` được gửi cho validator, và payload IDs được tạo cho các ca invalid. Harness cleanup dùng chính danh sách này và xác nhận không còn dòng khớp:

- `a449bef0-cc06-49a1-963e-237d226a0f0a`
- `1522d878-f899-489f-89ad-0c9803f85abf`
- `207cc6a4-5310-49bf-a348-5cf411c3a349`
- `b966c7f4-b423-4004-abaa-232f53166823`
- `df49322b-3cdf-4f9c-b063-4b6d1ec5a860`
- `9fbfdce2-176d-45aa-a137-50d838a207a1`
- `d36c5e66-5733-4178-a62d-3e2768e07a58`
- `e9ee4bc9-cfbc-44f9-b154-59e5a44c5632`
- `6c819dae-1657-4d20-b925-71f9256b944b`
- `6b3c864b-9718-463b-9bd5-c9a68387cc9d`
- `6ba0815d-57a6-4796-9a59-cdb88b808048`
- `not-a-uuid`
- `1b2c5652-5c57-4afe-bd3e-5a83e13f21a3`
- `d3df29a6-d95b-4e4f-a7d6-04e6a667a070`
- `e8fbfc53-e042-448e-a17e-59d1e607e3cc`
- `f2ad9aa9-4ee0-4c90-9171-765035588871`
- `763680b0-039b-4187-a820-a74ec6057537`
- `3e2e5f7d-81ec-4b8d-8a74-69ffde08d527`
- `d1291dc0-33e1-4f72-83b7-49a93f0b7209`
- `4dff59f4-7935-431d-98f6-d25480e138c3`
- `fcf32619-d222-4e3c-8ee8-67ad688e9c02`
- `ac69b9b2-96e0-4403-8b39-e8ee3ef4d781`
- `0db2c913-2be6-4ecb-9e7d-55dee7e81809`
- `a750a74c-221a-4154-8d40-6045facaaec0`
- `e1f93e11-4d2b-4b98-98be-8b72964e82d9`
- `b2f62bcc-c593-477e-8d56-ac538d0c2949`
- `9c6f86b5-773e-4744-af27-78d326d3c651`
- `a818658c-9799-4e93-bfef-0c5071d16021`
- `0e9ef019-f9ed-4211-a9f0-a3ac324fb9ae`
- `0d5cf272-f74c-4c54-b1be-f334ac86a2b9`
- `1a991c59-1038-4a05-ab03-62c21c5f9547`
- `cbe268ad-3a42-47e5-83c4-3ea6fc3c6aa5`
- `ba96ed37-c835-4906-8c50-ec3e97c31d8f`
- `9f8f3b87-357b-4eb4-ab23-5518043dda65`
- `18fd041c-b5eb-4bd1-b9e9-0e405e34f67f`
- `b8cab459-1b8a-47d8-89b5-64f48010bc91`
- `345f72f8-daea-4f74-9b82-c9bf2fd950de`
- `63dd32ac-185a-4566-9152-9fca22324556`
- `8ce39426-a6fe-4a5d-886e-2a262a3e9adf`
- `c9548180-20f0-4d15-9eed-13212b58ce72`
- `75e4a2ca-a013-4008-aa26-49c7497067c3`
- `5b8de746-4eb5-44a1-b6eb-0848b8c5f110`
- `79f82c70-140b-4897-af9e-2e9634e6c0d3`
- `e017d04b-6089-4436-ba22-6e7e0ecaf506`
- `6d8f697f-3757-445c-890f-707eb83aa574`
- `7fcdab66-364f-4c39-8a30-bbf7050eb34f`
- `745f0343-8258-46fe-be78-522b663ca527`
- `51d70d22-b8c9-475c-bf33-9275c7d6f810`
- `b915a9ce-83e4-488c-8318-eee85c670661`
- `358126a9-51da-4a46-beba-58305b486324`
- `7ff2d912-22fd-45ff-bde5-1383f088d1d7`
- `d5313068-6052-4a4b-987b-636a10293ce3`
- `6c76783e-5044-4b38-b2b8-b74f08fbd570`
- `a3bff8e9-fcd4-4ade-89e8-7d3c5e627772`
- `1056b17a-02ed-42d3-9a64-6623d0d1ea55`
- `6e4306dc-f9ba-40d4-9a64-7ca687391f4e`
- `748b1041-8027-4bf9-b939-3e64fcfa9375`
- `04c76eaf-77e2-4f2c-b03d-e27404b62e4b`
- `d63730a6-5332-47c0-88bf-ec64ea43695c`
- `f2c37f5c-735b-4ac5-8bab-3162637347d9`
- `3043d84b-97c4-4aa3-af51-c488307e2265`
- `ea19254c-4f05-4fe0-89f8-2753e86bd56f`
- `0961b4bd-61bd-4fdd-9113-ce490bdc8218`
- `855d7515-92a5-464a-812d-2093276aabee`
- `8285769f-5acf-4a04-934a-6a9165cb0024`
- `404afeeb-38cb-4c0f-9166-84e9232eb0f0`
- `c65cd3e4-6279-4cec-bdce-4d736f61e0b1`
- `2c700c44-4c9c-4f26-9435-0caae7780ad4`
- `3cce4007-9af6-4149-b15e-e833ebd806e7`
- `6a205325-0e04-4eb5-85db-b3ff61add15a`
- `3f090a72-9e07-4431-9add-da3ce95bc31c`
- `c86d9116-977d-4304-9994-9ee0bc6623f9`
- `4f94ea1e-1e47-44b5-9dca-17986978053e`
- `c9a10d46-fe02-4abc-b177-d186f84938f2`
- `9781e427-67f1-41c0-a1fb-3a9b4c4bff82`
- `131377cf-f48c-47c8-a3f0-d0170f11025a`
- `09bd6e64-b040-42eb-9c66-2ca5f608a8e1`

## Dọn stack sau chạy

Lệnh chạy: `docker compose -p posture-test -f docker-compose.test.yml down` (không `-v`). Output: hai container `posture-test-mqtt-broker-1` và `posture-test-postgres-1` chuyển sang Stopped rồi Removed; network `posture-test_default` Removed. Lệnh `docker compose -p posture-test -f docker-compose.test.yml ps` sau đó chỉ in header, không còn container.

`run_checks.py` là harness tạm được dùng trong lượt kiểm tra; đã xóa sau khi chạy cùng file output tạm. Không còn file harness ở repo; kết quả và các UUID được giữ trong báo cáo này. Output JSON nguyên văn cho status/body lỗi được ghi ở trên; body danh sách GET thành công được tóm tắt bằng số dòng và điều kiện đã đối chiếu để tránh lặp lại 50 bản ghi.
