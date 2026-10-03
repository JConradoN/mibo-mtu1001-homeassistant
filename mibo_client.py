#!/usr/bin/env python3
"""Cliente nao-oficial da API REST do Mibo/Dahua (pcs/v1), usado pelos apps
Intelbras Mibo / Dahua Easy4ip / Imou para controlar cameras e sensores IoT
(incluindo sensores Zigbee pareados via hub, ex: Intelbras MTU 1001 + MCA 1002).

Implementa a assinatura HMAC-SHA256 exigida pelo header x-pcs-signature.
A chave usada e uma constante fixa, embutida no app (nao depende de senha de
conta nem de sessao) -- extraida via instrumentacao em tempo de execucao
(ver METHODOLOGY.md para o processo completo).

Uso:
    export MIBO_USERNAME='uuid\\<seu_uuid>'
    export MIBO_PRODUCT_ID='<productId do dispositivo>'
    export MIBO_DEVICE_ID='<deviceId do dispositivo>'
    python3 mibo_client.py
"""
import hashlib
import hmac
import base64
import json
import os
import random
import string
from datetime import datetime, timezone

import requests

USERNAME = os.environ["MIBO_USERNAME"]
PRODUCT_ID = os.environ["MIBO_PRODUCT_ID"]
DEVICE_ID = os.environ["MIBO_DEVICE_ID"]

# Chave HMAC fixa do app (nao e segredo de conta -- esta embutida no APK
# publico e e identica para todos os usuarios). Ver METHODOLOGY.md.
SIGNING_KEY = "8b1e940ed6cf7c3fbdb4e5f42335c2ac"

APIVER = "191204"
BASE = "https://app-sp2.easy4ipcloud.com/pcs/v1"

CLIENT_UA_JSON = {
    "country": "BR", "userLabel": "5", "terminalBrand": "generic",
    "project": "Intelbras9be0d3bb", "clientOS": "Android", "language": "pt_BR",
    "terminalId": "0000000000000000", "clientVersion": "V3.1.1",
    "ttid": "00000000000000000000000000000000", "terminalModel": "generic",
    "terminalName": "generic", "clientType": "phone",
    "clientProtocolVersion": "V7.4.7", "timezoneOffset": "-10800",
    "clientOV": "Android 11", "appid": "Intelbrasphone25aa", "darkMode": "light",
}
CLIENT_UA = base64.b64encode(json.dumps(CLIENT_UA_JSON, separators=(",", ":")).encode()).decode()


def _nonce():
    rand = "".join(random.choices(string.ascii_letters + string.digits, k=30))
    return str(int(datetime.now().timestamp() * 1000)) + rand


def _iso_date():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sign(method, path, body_bytes, content_type="application/json; charset=utf-8"):
    """Monta os headers x-pcs-* assinados para uma chamada a /pcs/v1/<path>."""
    content_md5 = base64.b64encode(hashlib.md5(body_bytes).digest()).decode()
    date = _iso_date()
    nonce = _nonce()
    full_path = "/pcs/v1" + path
    string_to_sign = (
        f"{method}\n{full_path}\n{content_md5}\n{content_type}\n"
        f"x-pcs-apiver:{APIVER}\n"
        f"x-pcs-client-ua:{CLIENT_UA}\n"
        f"x-pcs-date:{date}\n"
        f"x-pcs-nonce:{nonce}\n"
        f"x-pcs-username:{USERNAME}\n"
    )
    signature = base64.b64encode(
        hmac.new(SIGNING_KEY.encode(), string_to_sign.encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "x-pcs-apiver": APIVER,
        "x-pcs-nonce": nonce,
        "x-pcs-date": date,
        "x-pcs-signature": signature,
        "x-pcs-username": USERNAME,
        "x-pcs-client-ua": CLIENT_UA,
        "Content-MD5": content_md5,
        "Content-Type": content_type,
    }


def call(path, data, verbose=True):
    body = json.dumps({"data": data}, separators=(",", ":")).encode()
    headers = sign("POST", path, body)
    r = requests.post(BASE + path, data=body, headers=headers, timeout=15)
    if verbose:
        print("status:", r.status_code)
        try:
            print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        except Exception:
            print(r.text[:2000])
    return r


def get_sensor(verbose=True):
    """Chama device.info.BasicInfoGet e devolve o JSON completo do dispositivo
    (inclui 'properties', onde os data points do sensor ficam)."""
    r = call("/device.info.BasicInfoGet", {"productId": PRODUCT_ID, "deviceId": DEVICE_ID}, verbose=verbose)
    j = r.json()
    if verbose:
        props = j.get("data", {}).get("properties", {})
        print(
            f"\n--- Sensor ---\n"
            f"temperatura (16000): {props.get('16000')} C\n"
            f"umidade (16100): {props.get('16100')} %\n"
            f"bateria/sinal (11600): {props.get('11600')}\n"
            f"online (15900): {props.get('15900')}"
        )
    return j


if __name__ == "__main__":
    get_sensor()
