from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MeterParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meters = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("role") == "meter":
            self.meters.append(attributes)


def test_empty_dashboard_meters_have_valid_nonzero_range():
    parser = MeterParser()
    parser.feed((ROOT / "web/index.html").read_text(encoding="utf-8"))
    assert parser.meters
    assert all(int(meter["aria-valuemax"]) >= 1 for meter in parser.meters)


def test_dynamic_lists_are_not_live_regions_but_status_is():
    markup = (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert 'id="seat-map" class="seat-map" aria-live' not in markup
    assert 'id="history" class="event-list" aria-live' not in markup
    assert 'id="freshness-status" class="freshness-status" role="status" aria-live="polite"' in markup
    assert 'id="page-caption" aria-live="polite"' in markup


def test_dashboard_keeps_esp32_stream_controls_without_laptop_webcam():
    markup = (ROOT / "web/index.html").read_text(encoding="utf-8")
    script = (ROOT / "web/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "web/style.css").read_text(encoding="utf-8")

    assert 'id="camera-url"' in markup
    assert 'id="camera-start"' in markup
    assert 'id="camera-stop"' in markup
    assert 'id="camera-preview"' in markup
    assert "camera-laptop" not in markup + script
    assert "getUserMedia" not in script
    assert "camera-webcam" not in markup + script + styles
    assert ".camera-frame video" not in styles
