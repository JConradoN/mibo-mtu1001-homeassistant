"""Constantes do componente mibo_sensor."""

DOMAIN = "mibo_sensor"

CONF_USERNAME = "username"
CONF_PRODUCT_ID = "product_id"
CONF_DEVICE_ID = "device_id"

DEFAULT_NAME = "Sensor Mibo"
UPDATE_INTERVAL_SECONDS = 300

# codigos de data point (descobertos por engenharia reversa, ver METHODOLOGY.md)
DP_TEMPERATURE = "16000"
DP_HUMIDITY = "16100"
DP_BATTERY = "11600"
DP_ONLINE = "15900"
