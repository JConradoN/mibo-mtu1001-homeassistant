"""Constantes do componente mibo_sensor."""

DOMAIN = "mibo_sensor"

CONF_USERNAME = "username"
CONF_PRODUCT_ID = "product_id"
CONF_DEVICE_ID = "device_id"

DEFAULT_NAME = "Sensor Mibo"
# o sensor fisico (MTU1001) so reporta pra nuvem ~1x/min -- pollar mais rapido
# que isso so gasta chamada de API sem reduzir o atraso real; pollar mais
# devagar e atraso evitavel. 60s casa com o ciclo real do hardware.
UPDATE_INTERVAL_SECONDS = 60

# codigos de data point (descobertos por engenharia reversa, ver METHODOLOGY.md)
DP_TEMPERATURE = "16000"
DP_HUMIDITY = "16100"
DP_BATTERY = "11600"
DP_ONLINE = "15900"
