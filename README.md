
# Meshcore Observer for Home Assistant <img src="https://brands.home-assistant.io/_/homeassistant/icon.png" alt="Home Assistant" width="80"/> <img src="https://cdn.jsdelivr.net/gh/selfhst/icons/webp/meshcore.webp" alt="Meshcore" width="80"/>

![alt text](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-41BDF5?style=flat-square&logo=homeassistant)
![alt text](https://img.shields.io/badge/HACS-Compatible-8A2BE2?style=flat-square&logo=homeassistantcommunitystore)
![alt text](https://img.shields.io/badge/Meshcore-Observer-darkblue?style=flat-square&logo=traefikmesh)
![alt text](https://img.shields.io/badge/API-meshcoretel.ru-darkblue?style=flat-square&logo=traefikmesh)

![alt text](https://img.shields.io/badge/Status-in%20progress-2E8B57?style=for-the-badge&logo=Buddy)

### Integration for Home Assistant to monitor Vbart's Meshcore repeater via `/login` + `/api/stats`
Fetches telemetry from Meshcore repeater with [Vbart's Meshcore firmware](https://github.com/VBart/MeshCoreTel-firmware) and enriches neighbors data from [meshcoretel.ru](https://meshcoretel.ru).


<img width="400" alt="meshcore_card_1" src="https://github.com/user-attachments/assets/c74ae78e-e425-4a13-9052-ce98bb590b60" />
<img width="400" alt="meshcore_card_2" src="https://github.com/user-attachments/assets/337e58e7-5095-4035-b8f4-a45261a8072a" />

---

## 🛠️ Releases

[![Добавить интеграцию в Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=meshcore_observer)

[![Добавить репозиторий в HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=<YOUR_GITHUB>&repository=<YOUR_REPO>&category=integration)

> HACS / GitHub Releases:  
> [https://github.com/<YOUR_GITHUB>/meshcore_observer/releases](https://github.com/<YOUR_GITHUB>/meshcore_observer/releases)

---

## 💎 Features

>* UI setup via Config Flow (без YAML)
>* Auth flow: `POST /login` → token → `GET /api/stats`
>* Configurable update interval (**min 120 sec**)
>* SSL options:
>   * Verify SSL on/off
>   * Legacy TLS mode
>* Block selection in settings:
>   * `history`
>   * `archive`
>   * `core`
>   * `radio`
>   * `packets`
>   * `memory`
>   * `wifi`
>   * `services`
>   * `sensors`
>   * `neighbors_detail`
>* Neighbor enrichment by `full_id`:
>   * `https://meshcoretel.ru/api/observers/<full_id>`
>   * fallback: `https://meshcoretel.ru/api/nodes/<full_id>/repeater-dashboard`
>* Rate-limit protection:
>   * cache
>   * backoff on HTTP 429
>   * controlled enrichment per update cycle
>* Separate entity for dashboard card: **Neighbors List**

---

## 🚀 How to start

>* Install via **HACS** (Custom repository) or manually
>* Restart Home Assistant
>* Go to **Settings → Devices & Services → Add Integration**
>* Choose **Meshcore Observer**
>* Fill:
>   * Base URL (`http://...` or `https://...`)
>   * Password
>   * Scan interval (>=120)
>   * SSL options
>   * Enabled blocks
>* Save and open created device/entities

---

## ⚙️ API Example

```bash
BASE_URL="https://192.168.1.123"
PASSWORD="your-admin-password"

TOKEN=$(curl -sk -X POST "$BASE_URL/login" --data "$PASSWORD")

echo "Сводка:"
curl -sk "$BASE_URL/api/stats" \
  -H "X-Auth-Token: $TOKEN"
```

---

## 📳 Entities

>* `sensor.meshcore_observer_status`
>* `sensor.meshcore_observer_snr`
>* `sensor.meshcore_observer_rssi`
>* `sensor.meshcore_observer_wifi_ssid`
>* `sensor.meshcore_observer_wifi_rssi`
>* `sensor.meshcore_observer_packets_rx`
>* `sensor.meshcore_observer_packets_tx`
>* `sensor.meshcore_observer_mqtt`
>* `sensor.meshcore_observer_neighbors_list` (+ `neighbors` attributes for card)

---

## 👥 Neighbors fields

For each neighbor in `neighbors`:

>* `id`
>* `full_id`
>* `observer`
>* `model`
>* `last_message_at`
>* `snr_db`

---

## 🧩 Example Lovelace Card (Neighbors)

```yaml
type: markdown
title: 👥 Meshcore · Соседи
content: >
  {% set ent = 'sensor.meshcore_observer_neighbors_list' %}
  {% set rows = state_attr(ent, 'neighbors') or [] %}
  {% if rows | count == 0 %}
  _Нет данных по соседям_
  {% else %}
  **Всего:** {{ rows|count }}
  ---
  {% for n in rows | sort(attribute='snr_db', reverse=True) %}
  {% set snr = (n.snr_db if n.snr_db is not none else -999) | float %}
  {% set mark = '🟢' if snr >= 5 else ('🟡' if snr >= 0 else '🔴') %}
  **{{ mark }} {{ n.id }} — {{ n.observer if n.observer else 'unknown' }}**
  {{ (n.model if n.model else 'repeater') }}
  SNR: {{ '%.2f'|format(snr) }} dB
  {{ n.last_message_at if n.last_message_at else 'unknown' }}
  ---
  {% endfor %}
  {% endif %}
```

---

## ⚠️ Troubleshooting

>* `SSLV3_ALERT_HANDSHAKE_FAILURE`  
>  → try `http://` URL, or disable Verify SSL + enable Legacy TLS
>* `HTTP 429` from meshcoretel  
>  → increase interval (`300-900s`), enrichment runs gradually with backoff
>* `unknown` in neighbors fields  
>  → wait for enrichment cycle / check meshcoretel availability from HA container
>* entities `unavailable`  
>  → check credentials, node URL, and HA logs

---

## 📑 Dependencies

>* Home Assistant Core
>* aiohttp (bundled with HA)
>* Custom integration API (DataUpdateCoordinator, ConfigFlow)



[![Добавить репозиторий в HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=<YOUR_GITHUB>&repository=<YOUR_REPO>&category=integration)
