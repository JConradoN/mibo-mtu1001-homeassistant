"""Cliente da API nao-oficial pcs/v1 do Mibo/Dahua. So biblioteca padrao
(urllib/hashlib/hmac) -- ver METHODOLOGY.md do repo pra como a assinatura
foi descoberta."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import random
import string
import urllib.error
import urllib.request
from datetime import datetime, timezone

# chave HMAC fixa do app (nao e segredo de conta -- embutida no APK publico,
# igual pra todo mundo). Ver METHODOLOGY.md.
SIGNING_KEY = "8b1e940ed6cf7c3fbdb4e5f42335c2ac"
APIVER = "191204"
BASE = "https://app-sp2.easy4ipcloud.com/pcs/v1"

_CLIENT_UA_JSON = {
    "country": "BR", "userLabel": "5", "terminalBrand": "generic",
    "project": "Intelbras9be0d3bb", "clientOS": "Android", "language": "pt_BR",
    "terminalId": "0000000000000000", "clientVersion": "V3.1.1",
    "ttid": "00000000000000000000000000000000", "terminalModel": "generic",
    "terminalName": "generic", "clientType": "phone",
    "clientProtocolVersion": "V7.4.7", "timezoneOffset": "-10800",
    "clientOV": "Android 11", "appid": "Intelbrasphone25aa", "darkMode": "light",
}
CLIENT_UA = base64.b64encode(json.dumps(_CLIENT_UA_JSON, separators=(",", ":")).encode()).decode()


class MiboApiError(Exception):
    """Erro generico de comunicacao com a API do Mibo."""


def _nonce() -> str:
    rand = "".join(random.choices(string.ascii_letters + string.digits, k=30))
    return str(int(datetime.now().timestamp() * 1000)) + rand


def _iso_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sign(username: str, method: str, path: str, body_bytes: bytes,
          content_type: str = "application/json; charset=utf-8") -> dict[str, str]:
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
        f"x-pcs-username:{username}\n"
    )
    signature = base64.b64encode(
        hmac.new(SIGNING_KEY.encode(), string_to_sign.encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "x-pcs-apiver": APIVER,
        "x-pcs-nonce": nonce,
        "x-pcs-date": date,
        "x-pcs-signature": signature,
        "x-pcs-username": username,
        "x-pcs-client-ua": CLIENT_UA,
        "Content-MD5": content_md5,
        "Content-Type": content_type,
    }


def get_sensor_properties(username: str, product_id: str, device_id: str) -> dict:
    """Chamada bloqueante (rodar via hass.async_add_executor_job).
    Devolve o dict 'properties' do dispositivo (codigos DP_* de const.py)."""
    body = json.dumps(
        {"data": {"productId": product_id, "deviceId": device_id}},
        separators=(",", ":"),
    ).encode()
    headers = _sign(username, "POST", "/device.info.BasicInfoGet", body)
    req = urllib.request.Request(BASE + "/device.info.BasicInfoGet", data=body,
                                  headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read())
    except urllib.error.URLError as err:
        raise MiboApiError(f"falha de rede: {err}") from err

    if payload.get("code") != 10000:
        raise MiboApiError(f"erro da API: {payload}")

    return payload.get("data", {}).get("properties", {})
