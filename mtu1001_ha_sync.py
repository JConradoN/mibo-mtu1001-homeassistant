#!/usr/bin/env python3
"""Le o sensor MTU1001 (via mibo_client) e publica o estado no Home Assistant
pela API REST (POST /api/states/<entity_id>). Pensado pra rodar em cron/timer."""
import json
import os

import requests

from mibo_client import get_sensor

HA_URL = os.environ.get("HA_URL", "http://localhost:8123")
HA_TOKEN = os.environ["HA_TOKEN"]
HEADERS = {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}


def push_state(entity_id, state, attributes):
    r = requests.post(
        f"{HA_URL}/api/states/{entity_id}",
        headers=HEADERS,
        data=json.dumps({"state": state, "attributes": attributes}),
        timeout=10,
    )
    r.raise_for_status()


def main():
    j = get_sensor(verbose=False)
    props = j.get("data", {}).get("properties", {})
    temp = props.get("16000")
    humidity = props.get("16100")
    battery = props.get("11600")
    online = props.get("15900")

    push_state("sensor.mtu1001_temperatura", temp, {
        "friendly_name": "MTU1001 Temperatura",
        "unit_of_measurement": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
        "icon": "mdi:thermometer",
    })
    push_state("sensor.mtu1001_umidade", humidity, {
        "friendly_name": "MTU1001 Umidade",
        "unit_of_measurement": "%",
        "device_class": "humidity",
        "state_class": "measurement",
        "icon": "mdi:water-percent",
    })
    push_state("sensor.mtu1001_bateria", battery, {
        "friendly_name": "MTU1001 Bateria/Sinal",
        "unit_of_measurement": "%",
        "device_class": "battery",
        "state_class": "measurement",
        "icon": "mdi:battery",
    })
    push_state("binary_sensor.mtu1001_online", "on" if online == 1 else "off", {
        "friendly_name": "MTU1001 Online",
        "device_class": "connectivity",
    })

    print(f"OK temp={temp} umid={humidity} bateria={battery} online={online}")


if __name__ == "__main__":
    main()
