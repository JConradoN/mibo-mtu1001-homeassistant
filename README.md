# mibo-mtu1001-homeassistant

Leitura local/automatizada do sensor Zigbee de temperatura e umidade **Intelbras MTU 1001**
(pareado via hub **MCA 1002**) e integração com o **Home Assistant** — sem precisar manter o
app **Mibo** aberto, sem root no celular, sem comprar um segundo coordenador Zigbee.

> Projeto irmão de [izy-connect-homeassistant](https://github.com/JConradoN/izy-connect-homeassistant)
> (mesmo problema, outro aparelho/protocolo).

## O problema

O MTU 1001 é um sensor Zigbee genuíno, mas ele não expõe nada na sua rede local: ele fala
Zigbee só com o hub MCA 1002, e o hub conversa com a nuvem da Dahua/Imou (empresa que a
Intelbras usa como fornecedora/white-label por trás do app Mibo). O app mostra os dados, mas
não existe nenhuma API local documentada, nem um jeito oficial de ler os valores de outro
lugar (Home Assistant, script, etc).

## A solução

Depois de confirmar que o protocolo é 100% dependente da nuvem (ver `METHODOLOGY.md`), a saída
viável foi replicar a chamada REST que o próprio app faz — ela usa uma chave de assinatura
**fixa, embutida no APK** (não depende de senha de conta nem de sessão), então dá pra assinar
chamadas direto de um script Python, pra sempre, sem nunca mais abrir o app.

```
┌─────────────┐   Zigbee    ┌───────────┐   HTTPS (nuvem    ┌──────────────┐
│  MTU 1001   │ ──────────► │ MCA 1002  │   Dahua/Imou)     │ app-sp2.     │
│  (sensor)   │             │  (hub)    │ ────────────────► │ easy4ipcloud │
└─────────────┘             └───────────┘                   └──────┬───────┘
                                                                     │ POST /pcs/v1/
                                                                     │ device.info.BasicInfoGet
                                                                     │ (assinado com a chave fixa)
                                                              ┌──────▼───────┐
                                                              │ mibo_client.py│
                                                              └──────┬───────┘
                                                                     │ POST /api/states/...
                                                              ┌──────▼───────┐
                                                              │ Home Assistant│
                                                              └──────────────┘
```

**Importante:** isso não é um protocolo *local* no sentido Zigbee2MQTT/tinytuya — ainda passa
pela nuvem da Dahua. É "local" no sentido de que você lê o dado automaticamente, de um script
seu, sem abrir o app, sem depender da UI do Mibo renderizar nada.

## O que tem aqui

| Arquivo | O que faz |
|---|---|
| `mibo_client.py` | Cliente Python puro da API `pcs/v1` do Mibo/Dahua — assina e faz a chamada que lê os dados do sensor. |
| `mtu1001_ha_sync.py` | Usa o `mibo_client` e publica os valores no Home Assistant via API REST (`POST /api/states/...`). |
| `systemd/` | Unit + timer pra rodar o sync a cada 5 minutos automaticamente (systemd user). |
| `METHODOLOGY.md` | Processo completo de engenharia reversa: o que foi tentado, o que falhou e por quê, como a chave de assinatura foi extraída. |
| `.env.example` | Template de configuração (copie pra `.env.local`, preencha com seus dados). |

## Como usar

### 1. Descobrir os identificadores do seu dispositivo

Você precisa de 3 valores específicos da sua conta/dispositivo: `MIBO_USERNAME` (um UUID
interno, não é seu e-mail/telefone), `MIBO_PRODUCT_ID` e `MIBO_DEVICE_ID`. Esses valores
aparecem em qualquer chamada da API capturada com o app — o processo completo (interceptação
TLS + bypass de pinning) está documentado em `METHODOLOGY.md`. Não existe hoje um jeito mais
simples (sem decifrar o tráfego do app uma vez) de descobrir esses IDs.

### 2. Configurar

```bash
cp .env.example .env.local
# edite .env.local com os valores do passo 1 + seu token do Home Assistant
source .env.local
pip install requests
python3 mibo_client.py        # testa a leitura
python3 mtu1001_ha_sync.py    # testa a publicação no HA
```

Gerar o `HA_TOKEN`: no Home Assistant, Perfil → Segurança → "Long-Lived Access Tokens" → Criar.

### 3. Automatizar (systemd user)

```bash
mkdir -p ~/.config/systemd/user
cp systemd/mtu1001-ha-sync.* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now mtu1001-ha-sync.timer
```

Isso cria 4 entidades no HA, atualizadas a cada 5 min:
- `sensor.mtu1001_temperatura` (°C)
- `sensor.mtu1001_umidade` (%)
- `sensor.mtu1001_bateria` (%, sinal/qualidade)
- `binary_sensor.mtu1001_online`

## Caminho alternativo mais robusto (investigar antes de expandir isto)

O Home Assistant já tem uma integração **oficial** `imou` (mantida pelo próprio fabricante,
`codeowners: @Imou-OpenPlatform`), que usa a API **oficial e documentada** do Imou Open
Platform (`pyimouapi`), não a API de consumidor que este projeto usa por engenharia reversa.

Essa integração oficial já define tipos de sensor `temperature_current`, `humidity_current` e
`battery` — e tem endpoints (`getIotDeviceProperties`, `getIotDeviceDetailInfo`) com cara muito
parecida com o que descobrimos aqui. É bem possível que o MTU 1001 **já seja suportado** por
essa integração oficial, sem precisar de nada deste repositório — bastaria:

1. Criar conta developer no Imou Open Platform (console deles).
2. Gerar App ID + App Secret.
3. Vincular a conta/dispositivos do Mibo ao projeto developer (processo parecido com o Tuya
   Cloud Project — e, como em outros white-labels da Intelbras, existe risco real do app
   bloquear esse vínculo de propósito).

**Não testado ainda** — exige cadastro/ação direta do usuário, fora do escopo automatizável.
Se isso funcionar, a abordagem oficial é estritamente melhor (suportada pelo fabricante, não
quebra em atualização de app) e esse repositório vira desnecessário pra quem conseguir migrar.

## Aviso

Isso é engenharia reversa de uma API não documentada e não oficial. A Dahua/Intelbras pode
mudar qualquer coisa (endpoint, formato, chave de assinatura) numa atualização do app, sem
aviso, quebrando este projeto. Use por sua conta e risco — não há suporte do fabricante, nem
garantia de que vai continuar funcionando.

## Licença

MIT — ver `LICENSE`.
