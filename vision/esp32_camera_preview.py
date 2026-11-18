"""Local Streamlit preview for an ESP32-CAM MJPEG stream."""

from __future__ import annotations

from pathlib import Path
import sys
from urllib.parse import urlparse

import streamlit as st
import cv2
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vision.camera_preview import (
    PosePreview,
    analyze_frame,
)
from vision.capture import VideoCaptureStream
from vision.main import load_config
from vision.pose_estimator import PoseEstimator


CONFIG_PATH = Path(__file__).with_name("config.yaml")


@st.cache_resource(show_spinner=False)
def load_estimator(model_path: str, confidence: float) -> PoseEstimator:
    """Cache model weights in process memory, never image frames."""
    return PoseEstimator(model_path, confidence)


def resolve_local_model(model_name: str) -> Path | None:
    """Find existing local weights without triggering an automatic download."""
    configured = Path(model_name).expanduser()
    candidates = (
        configured,
        PROJECT_ROOT / configured,
        Path(__file__).parent / configured.name,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def draw_pose_overlay(frame: Image.Image, detections: list[PosePreview]) -> Image.Image:
    """Draw only shoulder/hip landmarks and trunk segments on a copy."""
    rendered = frame.copy()
    draw = ImageDraw.Draw(rendered)
    for detection in detections:
        shoulders = _midpoint(
            detection.keypoints.get("left_shoulder"),
            detection.keypoints.get("right_shoulder"),
        )
        hips = _midpoint(
            detection.keypoints.get("left_hip"),
            detection.keypoints.get("right_hip"),
        )
        for point in (shoulders, hips):
            if point is not None:
                x, y = point
                draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#00d084")
        if shoulders is not None and hips is not None:
            draw.line((shoulders, hips), fill="#00d084", width=3)
    return rendered


def _midpoint(first, second):
    if first is None or second is None:
        return None
    return ((float(first[0]) + float(second[0])) / 2, (float(first[1]) + float(second[1])) / 2)


def close_stream() -> None:
    """Release the active network camera connection, if any."""
    stream = st.session_state.pop("esp32_stream", None)
    if stream is not None:
        stream.close()


def render_analysis(
    frame: Image.Image,
    config,
    model_path: Path | None,
) -> None:
    """Render pose analysis for a transient in-memory frame."""
    if model_path is None:
        st.info("Đã nhận khung hình. Cần đặt model weights cục bộ để chạy nhận diện pose.")
        return
    try:
        estimator = load_estimator(
            str(model_path), float(config["model"]["keypoint_confidence"])
        )
        detections = analyze_frame(
            frame, estimator, config["classifier"], config["seat_regions"]
        )
    except Exception as error:
        st.error(f"Không xử lý được khung hình ({type(error).__name__}): {error}")
        return

    st.image(
        draw_pose_overlay(frame, detections),
        caption="Ảnh và landmarks chỉ tồn tại trong phiên xử lý hiện tại.",
    )
    if not detections:
        st.warning("Không phát hiện pose trong khung hình này.")
        return
    for index, detection in enumerate(detections, start=1):
        st.subheader(f"Pose {index}")
        left, middle, right = st.columns(3)
        left.metric("Nhãn", detection.label)
        middle.metric(
            "Góc thân",
            "Chưa xác định" if detection.trunk_angle is None else f"{detection.trunk_angle:.1f}°",
        )
        right.metric("Confidence pose", f"{detection.confidence:.2f}")
        st.write(f"seat_id: {detection.seat_id or 'Chưa gán — kiểm tra seat_regions trong config.yaml'}")


@st.fragment(run_every=0.5)
def render_esp32_stream(config, model_path: Path | None) -> None:
    """Read and analyze one latest ESP32-CAM frame per Streamlit refresh."""
    stream = st.session_state.get("esp32_stream")
    if stream is None:
        return
    frame = stream.read()
    if frame is None:
        st.warning("Đang mất luồng hoặc chưa nhận được frame. Kiểm tra Wi-Fi/URL rồi thử kết nối lại.")
        return
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame_rgb)
    st.image(image, caption="ESP32-CAM — frame tạm thời trong bộ nhớ, không lưu ra đĩa.")
    render_analysis(image, config, model_path)


def main() -> None:
    st.set_page_config(page_title="Vision camera preview", layout="centered")
    st.title("Kiểm tra camera — Vision")
    st.caption("Nhập URL ESP32-CAM để xem và xử lý luồng MJPEG.")
    st.info(
        "Chỉ chạy app trên máy cá nhân tại 127.0.0.1. Khung hình ESP32-CAM được xử lý "
        "trong tiến trình Streamlit cục bộ; app không ghi ảnh ra đĩa và không "
        "phát MQTT. Không dùng ảnh/video lớp học hoặc người chưa được phép."
    )

    try:
        config = load_config(CONFIG_PATH)
    except (OSError, RuntimeError, ValueError) as error:
        st.error(f"Không đọc được cấu hình Vision: {error}")
        st.stop()

    model_name = str(config["model"]["name"])
    model_path = resolve_local_model(model_name)
    if model_path is None:
        st.warning(
            f"Không tìm thấy model weights '{model_name}' trên máy. "
            "Camera vẫn kiểm tra được, nhưng inference bị tắt. Đặt file model đã được "
            "nhóm phê duyệt tại thư mục gốc repo hoặc vision/ để bật inference. "
            "App không tự tải weights."
        )

    enabled = st.checkbox("Tôi xác nhận chỉ dùng dữ liệu test được phép.")
    if not enabled:
        close_stream()
        st.caption("Xác nhận để bật camera. Chỉ dùng dữ liệu thử nghiệm được phép.")
        st.stop()

    st.subheader("Kết nối ESP32-CAM")
    st.caption("Nhập địa chỉ /stream hiển thị trong Serial Monitor, ví dụ http://192.168.1.105/stream")
    with st.form("esp32_connect_form"):
        stream_url = st.text_input(
            "URL luồng MJPEG", placeholder="http://192.168.1.105/stream",
            value=st.session_state.get("esp32_stream_url", ""),
        ).strip()
        connect_col, disconnect_col = st.columns(2)
        start = connect_col.form_submit_button("Kết nối / Bắt đầu")
        disconnect = disconnect_col.form_submit_button("Ngắt kết nối")

    if disconnect:
        close_stream()
        st.success("Đã ngắt kết nối ESP32-CAM.")
    if start:
        parsed = urlparse(stream_url)
        if parsed.scheme != "http" or not parsed.hostname:
            close_stream()
            st.error("URL không hợp lệ. Nhập địa chỉ HTTP đầy đủ, ví dụ http://192.168.1.105/stream.")
        else:
            close_stream()
            stream = VideoCaptureStream(
                stream_url, reconnect_delay_seconds=0.1,
                open_timeout_ms=3000, read_timeout_ms=3000,
            )
            if stream.connect():
                st.session_state.esp32_stream = stream
                st.session_state.esp32_stream_url = stream_url
                st.success("Đã kết nối. Đang đọc và xử lý frame mới nhất.")
            else:
                stream.close()
                st.error("Không kết nối được camera. Kiểm tra URL, nguồn ESP32-CAM và máy tính cùng mạng LAN.")

    if st.session_state.get("esp32_stream") is not None:
        st.success(f"Đang kết nối: {st.session_state.get('esp32_stream_url', '')}")
        render_esp32_stream(config, model_path)
    else:
        st.caption("Chưa kết nối camera.")
    return


if __name__ == "__main__":
    main()
