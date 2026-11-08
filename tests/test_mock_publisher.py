#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock Publisher: Gui ban tin gia lap de test backend va dashboard khong can camera/AI
Su dung cho Moc B va Moc C theo TESTING.md
"""

import sys
import os
import time
import json
import uuid
import datetime
import random

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Vui long cai dat: pip install paho-mqtt")
    sys.exit(1)

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "classroom/posture/events")

SEATS = ["S01", "S02", "S03", "S04"]
LABELS = ["upright", "slouching", "leaning", "unknown"]

def generate_mock_event(seat_id, force_label=None):
    label = force_label or random.choice(LABELS)
    trunk_angle = None if label == "unknown" else round(random.uniform(5.0, 35.0), 2)
    conf = round(random.uniform(0.75, 0.98), 2)

    return {
        "event_id": str(uuid.uuid4()),
        "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seat_id": seat_id,
        "label": label,
        "angles": {
            "trunk": trunk_angle
        },
        "confidence": conf,
        "model": "mock-generator-v1"
    }

def main():
    print(f"[Mock Publisher] Dang ket noi broker {MQTT_HOST}:{MQTT_PORT}...")
    client = mqtt.Client(client_id=f"mock_pub_{uuid.uuid4().hex[:6]}")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    print(f"[Mock Publisher] Bat dau gui du lieu mau len topic: {MQTT_TOPIC}")
    print("Nhan Ctrl+C de dung.")

    try:
        while True:
            for seat in SEATS:
                event = generate_mock_event(seat)
                payload = json.dumps(event)
                client.publish(MQTT_TOPIC, payload, qos=1)
                print(f"[Published] {event['seat_id']} -> {event['label']} (Goc: {event['angles']['trunk']} deg, Conf: {event['confidence']})")
                time.sleep(0.5)
            time.sleep(2.0)
    except KeyboardInterrupt:
        print("\n[Mock Publisher] Dung ban tin gia lap.")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
