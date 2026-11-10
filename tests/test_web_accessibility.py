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


def test_meter_updates_keep_maximum_at_least_one_and_guard_empty_width():
    script = (ROOT / "web/app.js").read_text(encoding="utf-8")
    assert "Math.max(1, items.length)" in script
    assert "items.length ? `${count / items.length * 100}%` : '0%'" in script
