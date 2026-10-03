"""Constantes do componente mibo_sensor."""

DOMAIN = "mibo_sensor"

CONF_USERNAME = "username"
CONF_PRODUCT_ID = "product_id"
CONF_DEVICE_ID = "device_id"

DEFAULT_NAME = "Sensor Mibo"
# CONFIRMADO (2026-10-03): polling agressivo (60s + varias chamadas manuais
# de teste em sequencia) faz a nuvem da Dahua comecar a servir um valor
# cacheado/obsoleto especificamente pro DP de umidade -- 5 minutos sem
# nenhuma chamada foi suficiente pra destravar (84.9% parado -> 74.69%
# fresco na volta). Nao e limitacao permanente do endpoint, e sensibilidade
# a frequencia de chamada do lado deles. 120s e mais conservador que o
# ciclo natural do sensor fisico (~60s) de proposito.
UPDATE_INTERVAL_SECONDS = 120

# codigos de data point (descobertos por engenharia reversa, ver METHODOLOGY.md)
DP_TEMPERATURE = "16000"
DP_HUMIDITY = "16100"
DP_BATTERY = "11600"
DP_ONLINE = "15900"
