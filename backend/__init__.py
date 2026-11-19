"""Backend for classroom posture events.

Các tầng (phụ thuộc chỉ đi từ trên xuống, xem docs/backend_architecture.md):

    interfaces/      giao tiếp vào/ra: HTTP API, MQTT consumer
    services/        nghiệp vụ: nhận event (retry, phân loại kết quả), truy vấn event
    repositories/    truy vấn SQL
    infrastructure/  kết nối PostgreSQL, áp dụng migration
    domain/          hợp đồng dữ liệu, kiểm tra payload/tham số, lỗi nghiệp vụ (thuần, không I/O)
    config.py        biến môi trường -> settings

Điểm vào (composition root): `python -m backend.api`, `python -m backend.mqtt_subscriber`.
"""
