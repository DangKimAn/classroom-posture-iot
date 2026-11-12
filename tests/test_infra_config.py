from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mosquitto_persistence_is_enabled_and_bounded():
    config = (ROOT / "mosquitto.conf").read_text(encoding="utf-8")
    assert "persistence true" in config
    assert "persistence_location /mosquitto/data/" in config
    assert "autosave_interval 30" in config
    assert "max_queued_messages 10000" in config


def test_compose_mounts_named_mosquitto_data_volume():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "mosquitto_data:/mosquitto/data" in compose
    assert "  mosquitto_data:" in compose


def test_database_values_share_single_compose_source():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "POSTGRES_PASSWORD: ${DB_PASSWORD:?Set DB_PASSWORD in .env}" in compose
    assert "DB_PASSWORD: ${DB_PASSWORD:?Set DB_PASSWORD in .env}" in compose
    assert "DB_URL: postgresql://" not in compose
