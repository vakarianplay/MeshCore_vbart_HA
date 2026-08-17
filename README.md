# Meshcore Observer for Home Assistant

Home Assistant custom integration for monitoring a Meshcore observer node with [Vbart's firmware](https://github.com/VBart/MeshCoreTel-firmware) for Meshcoretel.ru.

------------------------------

> Vbart's Meshcore firmware [https://github.com/VBart/MeshCoreTel-firmware](https://github.com/VBart/MeshCoreTel-firmware)
>
> MeshCoreTel [https://meshcoretel.ru](https://meshcoretel.ru)

-----------------

The integration connects to your node API, authenticates via `/login`, fetches `/api/stats`, and creates sensors for selected blocks (`radio`, `packets`, `wifi`, `services`, `history`, `archive`, `core`, `memory`, `sensors`, `neighbors_detail`).

For neighbors, it can enrich data from:

- `https://meshcoretel.ru/api/observers/<full_id>`
- fallback: `https://meshcoretel.ru/api/nodes/<full_id>/repeater-dashboard`

---

## Features

- UI setup (Config Flow)
- Configurable update interval (minimum 120 seconds)
- SSL options:
  - verify SSL on/off
  - legacy/insecure TLS mode
- Select which blocks to expose
- Neighbors list sensor with optional enrichment
- Single device in Home Assistant: **Meshcore Observer**

---

## Installation

### Option 1: HACS (Custom Repository)

1. Open **HACS** → **Integrations**.
2. Click the 3-dot menu → **Custom repositories**.
3. Add your repository URL.
4. Category: **Integration**.
5. Install **Meshcore Observer**.
6. Restart Home Assistant.
7. 

### Option 2: Manual

1. Copy `custom_components/meshcore_observer` to your HA config folder:
   - `/config/custom_components/meshcore_observer`
2. Restart Home Assistant.

---

## Configuration (UI)

Go to:

**Settings → Devices & Services → Add Integration → Meshcore Observer**

Fill in:

- **Base URL** (example: `https://192.168.1.123` or `http://zero.lan:1484`)
- **Password**
- **Update interval** (>= 120 sec)
- **Verify SSL**
- **Legacy TLS mode**
- **Blocks to include**

---

## Node API flow used

```bash
BASE_URL="https://192.168.1.123"
PASSWORD="your-admin-password"

TOKEN=$(curl -sk -X POST "$BASE_URL/login" --data "$PASSWORD")

curl -sk "$BASE_URL/api/stats" -H "X-Auth-Token: $TOKEN"
```

---

## Sensors created

Depending on selected blocks, integration creates sensors like:

- `Meshcore Status`
- `SNR`, `RSSI`
- `WiFi SSID`, `WiFi RSSI`
- `Packets RX`, `Packets TX`
- `MQTT`
- `Core Uptime`, `Core Errors`
- `Heap Free`
- `MCU Temp`
- `History Events`
- `Archive Available`
- `Neighbors List`

`Neighbors List` includes attribute `neighbors` with entries:

- `id`
- `full_id`
- `observer`
- `model`
- `last_message_at`
- `snr_db`

---

## Neighbors enrichment

When `neighbors_detail` block is enabled, integration tries to resolve:

1. `https://meshcoretel.ru/api/observers/<full_id>`
2. fallback `https://meshcoretel.ru/api/nodes/<full_id>/repeater-dashboard`

If external API is rate-limited (`HTTP 429`), integration applies back off and cache.

---

## Known limitations

- External API (`meshcoretel.ru`) may return `429 Too Many Requests`.
- During backoff, some neighbor fields can temporarily remain `null`.
- Some node firmware/API variants may differ in login/token response format.

---

## Recommended settings

- Update interval: `300`–`900` seconds
- Enable only needed blocks
- If local TLS is self-signed/broken:
  - `Verify SSL = false`
  - `Legacy TLS mode = true`
- If node is plain HTTP, use `http://...` URL

---

## Example Lovelace card (Neighbors)

```yaml
type: markdown
title: 👥 Meshcore · Соседи
content: >
  {% set ent = 'sensor.mo_est_mqtt_07_neighbors_list' %}
  {% set rows = state_attr(ent, 'neighbors') or [] %}
  {% if rows | count == 0 %}
  _Нет данных по соседям_
  {% else %}
  **Всего:** {{ rows|count }}
  ---
  {% for n in rows | sort(attribute='snr_db', reverse=True) %}
  **{{ n.id }} — {{ n.observer if n.observer else 'unknown' }}**
  {{ n.model if n.model else 'repeater' }}
  SNR: {{ n.snr_db }} dB
  {{ n.last_message_at if n.last_message_at else 'unknown' }}
  ---
  {% endfor %}
  {% endif %}
```

---

## Troubleshooting

### Integration adds but sensors are unavailable
- Check node URL/protocol (`http` vs `https`)
- Check password
- Try disabling SSL verification
- Check HA logs:
  - **Settings → System → Logs**
  - Search for `meshcore_observer`

### Neighbors show unknown fields
- External enrichment API may be rate-limited (`429`)
- Wait until backoff expires
- Increase update interval

### SSL handshake failure
- Use `http://` if node is not true HTTPS
- Or set:
  - `Verify SSL = false`
  - `Legacy TLS mode = true`

MIT
```
