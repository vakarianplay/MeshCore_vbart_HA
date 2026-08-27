from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

def snr_icon(v):
    if v is None:
        return "mdi:help-circle-outline"
    if v >= 5:
        return "mdi:signal-cellular-3"
    if v >= 0:
        return "mdi:signal-cellular-2"
    return "mdi:signal-cellular-1"

class BaseEntity(CoordinatorEntity):
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, "meshcore_main")},
            name="Meshcore Observer",
            manufacturer="Meshcore",
            model="Observer Node",
        )

class ValueSensor(BaseEntity, SensorEntity):
    def __init__(self, coordinator, name, uid, fn, unit=None, icon=None):
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = uid
        self._fn = fn
        self._attr_native_unit_of_measurement = unit
        self._icon_static = icon

    @property
    def native_value(self):
        d = self.coordinator.data or {}
        try:
            return self._fn(d)
        except Exception:
            return None

    @property
    def icon(self):
        if self._attr_unique_id.endswith("_snr"):
            return snr_icon(self.native_value)
        return self._icon_static

class NeighborsListSensor(BaseEntity, SensorEntity):
    _attr_name = "Neighbors List"
    _attr_unique_id = "meshcore_observer_neighbors_list"
    _attr_icon = "mdi:account-network"

    @property
    def native_value(self):
        return len((self.coordinator.data or {}).get("neighbors_detail", []))

    @property
    def extra_state_attributes(self):
        return {"neighbors": (self.coordinator.data or {}).get("neighbors_detail", [])}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    blocks = set(coordinator.blocks)

    entities = [
        ValueSensor(coordinator, "Meshcore Status", "meshcore_observer_status", lambda d: "ok", icon="mdi:radio-tower")
    ]

    if "radio" in blocks:
        entities.append(ValueSensor(coordinator, "SNR", "meshcore_observer_snr", lambda d: d.get("radio", {}).get("last_snr"), "dB"))
        entities.append(ValueSensor(coordinator, "RSSI", "meshcore_observer_rssi", lambda d: d.get("radio", {}).get("last_rssi"), "dBm"))

    if "packets" in blocks:
        entities.append(ValueSensor(coordinator, "Packets RX", "meshcore_observer_packets_rx", lambda d: d.get("packets", {}).get("recv")))
        entities.append(ValueSensor(coordinator, "Packets TX", "meshcore_observer_packets_tx", lambda d: d.get("packets", {}).get("sent")))

    if "wifi" in blocks:
        entities.append(ValueSensor(coordinator, "WiFi SSID", "meshcore_observer_wifi_ssid", lambda d: d.get("wifi", {}).get("ssid")))
        entities.append(ValueSensor(coordinator, "WiFi RSSI", "meshcore_observer_wifi_rssi", lambda d: d.get("wifi", {}).get("rssi"), "dBm"))

    if "services" in blocks:
        entities.append(ValueSensor(coordinator, "MQTT", "meshcore_observer_mqtt", lambda d: d.get("services", {}).get("mqtt_state")))

    if "core" in blocks:
        entities.append(ValueSensor(coordinator, "Core Uptime", "meshcore_observer_core_uptime", lambda d: d.get("core", {}).get("uptime_secs"), "s"))
        entities.append(ValueSensor(coordinator, "Core Errors", "meshcore_observer_core_errors", lambda d: d.get("core", {}).get("errors")))

    if "memory" in blocks:
        entities.append(ValueSensor(coordinator, "Heap Free", "meshcore_observer_heap_free", lambda d: d.get("memory", {}).get("heap_free"), "B"))

    if "sensors" in blocks:
        entities.append(ValueSensor(coordinator, "MCU Temp", "meshcore_observer_mcu_temp", lambda d: d.get("sensors", {}).get("mcu_temp_c"), "°C"))

    if "history" in blocks:
        entities.append(ValueSensor(coordinator, "History Events", "meshcore_observer_history_events", lambda d: d.get("history", {}).get("events")))

    if "archive" in blocks:
        entities.append(ValueSensor(coordinator, "Archive Available", "meshcore_observer_archive_available", lambda d: d.get("archive", {}).get("available")))

    if "neighbors_detail" in blocks:
        entities.append(NeighborsListSensor(coordinator))

    async_add_entities(entities)