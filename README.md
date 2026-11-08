# Hệ Thống IoT Giám Sát Tư Thế Ngồi Trong Lớp Học (Classroom Posture Monitor)

Đồ án IoT / AIoT phát hiện tư thế ngồi của sinh viên trong lớp học theo thời gian thực sử dụng **ESP32-CAM → YOLOv8 Pose → MQTT → Backend / CSDL → Web Dashboard**.

Dự án áp dụng chuẩn **Agent Protocol** để con người và các AI Agent (Antigravity, Claude Code, Cursor, Copilot) cộng tác đa mô-đun an toàn, không xung đột mã nguồn và không vi phạm hợp đồng dữ liệu.

---

## 📁 Cấu Trúc Dự Án (Repository Structure)

```text
.
├── AGENTS.md                   # 🎯 ĐIỂM VÀO DUY NHẤT cho mọi AI Agent & nhà phát triển
├── CLAUDE.md                   # Chỉ mục trỏ về AGENTS.md (dành cho Claude Code)
├── docs/                       # Tài liệu đồ án và hợp đồng hệ thống
│   ├── BUSINESS.md             # 📋 Nghiệp vụ, định nghĩa nhãn tư thế và các ca sử dụng
│   ├── FLOWS.md                # 🔄 Các luồng dữ liệu liên khối, sequence và xử lý sự cố
│   ├── RULES.md                # ⚖️ Bộ 7 quy tắc cứng, phân quyền module và tiêu chuẩn DoD
│   ├── TECHS.md                # ⚙️ Toàn bộ ngăn xếp công nghệ, phần cứng, AI và thư viện
│   ├── agent/                  # Chi tiết chuẩn Agent Protocol
│   │   ├── PROJECT_SUMMARY.md  # Tóm tắt dự án 1 trang
│   │   ├── SCOPE.md            # Phạm vi In-Scope / Out-of-Scope
│   │   ├── ARCHITECTURE.md     # Kiến trúc 3 khối & luồng dữ liệu
│   │   ├── DATA_CONTRACT.md    # Hợp đồng dữ liệu (Stream, MQTT, DB, API)
│   │   ├── CONVENTIONS.md      # Quy chuẩn code, commit, nhánh, test
│   │   ├── WORKFLOW.md         # Phân quyền module, Issue/PR, Definition of Done
│   │   ├── SECURITY_PRIVACY.md # Bảo mật & quyền riêng tư (Privacy-by-design)
│   │   ├── TESTING.md          # Mocking, 5 mốc ghép A–E, số đo thực nghiệm
│   │   ├── DECISIONS.md        # Nhật ký quyết định & các điểm mở (ADR)
│   │   ├── GLOSSARY.md         # Bảng thuật ngữ kỹ thuật
│   │   └── REPORT_GUIDE.md     # Hướng dẫn viết báo cáo IEEE 4 chương
│   ├── data_contract.md        # Hợp đồng dữ liệu chính thức sau mốc A
│   └── api_contract.md         # Hợp đồng API chính thức sau mốc A
├── .claude/skills/             # 🛠️ Bộ kỹ năng tự động hóa của Agent
│   ├── start-task/SKILL.md     # Nhận và triển khai một issue chuẩn mực
│   ├── change-contract/SKILL.md# Quy trình thay đổi hợp đồng dữ liệu an toàn
│   └── review-pr/SKILL.md      # Kiểm tra và review PR tự động
├── firmware/                   # [Thành viên 1] Mã nguồn ESP32-CAM MJPEG HTTP Stream
├── vision/                     # [Thành viên 2] Dịch vụ OpenCV + YOLOv8 Pose + MQTT Publisher
├── backend/                    # [Thành viên 3] MQTT Subscriber, SQLite/Postgres DB & REST API
├── web/                        # [Thành viên 3] Web Dashboard hiển thị thời gian thực & lịch sử
├── tests/                      # Kiểm thử tích hợp (Integration Tests) & Mocks
├── docker-compose.yml          # Triển khai nhanh MQTT Broker & Database môi trường dev
└── .env.example                # Khung biến môi trường mẫu (không chứa secret)
```

---

## 👥 Phân Công Trách Nhiệm 3 Khối

| Thành viên | Khối phụ trách | Thư mục sở hữu | Nhiệm vụ cốt lõi |
| :--- | :--- | :--- | :--- |
| **TV1** | **Thiết bị & Wi-Fi** | `firmware/` | ESP32-CAM phát MJPEG qua HTTP, đo độ trễ/ổn định, chống sụt áp |
| **TV2** | **Thị giác máy tính (AI/CV)** | `vision/` | Đọc stream, inference YOLOv8 Pose, tính góc thân, publish MQTT |
| **TV3** | **Dữ liệu & Giao diện** | `backend/`, `web/` | MQTT Broker, DB lưu trữ chống trùng, REST API, Web Dashboard |

---

## ⚡ Bắt Đầu Nhanh (Quick Start)

### 1. Dành cho Lập trình viên / Sinh viên
- Đọc [AGENTS.md](file:///home/na/code/final_iot/AGENTS.md) và [PROJECT_SUMMARY.md](file:///home/na/code/final_iot/docs/agent/PROJECT_SUMMARY.md) để nắm toàn bộ quy ước nhóm.
- Xem [DATA_CONTRACT.md](file:///home/na/code/final_iot/docs/agent/DATA_CONTRACT.md) trước khi code bất kỳ phần giao tiếp nào.

### 2. Dành cho AI Agent
- Mọi Agent khi được gọi trong thư mục này **phải đọc `AGENTS.md` đầu tiên**.
- Tuyệt đối tuân thủ **7 Quy tắc cứng (Hard Rules)**: Không sửa chéo thư mục, Không đổi hợp đồng ngầm, Không hallucinate số đo, Không lưu video/ảnh thô hay danh tính sinh viên.
