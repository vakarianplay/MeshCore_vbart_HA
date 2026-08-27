import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_BASE_URL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    CONF_INSECURE_TLS,
    CONF_BLOCKS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERIFY_SSL,
    DEFAULT_INSECURE_TLS,
    MIN_SCAN_INTERVAL,
    ALL_BLOCKS,
)

def _schema(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_BASE_URL, default=defaults.get(CONF_BASE_URL, "https://meshcore.local")): str,
            vol.Required(CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, "")): str,
            vol.Required(CONF_SCAN_INTERVAL, default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): vol.All(
                vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)
            ),
            vol.Required(CONF_VERIFY_SSL, default=defaults.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)): bool,
            vol.Required(CONF_INSECURE_TLS, default=defaults.get(CONF_INSECURE_TLS, DEFAULT_INSECURE_TLS)): bool,
            vol.Required(CONF_BLOCKS, default=defaults.get(CONF_BLOCKS, ALL_BLOCKS)): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=ALL_BLOCKS,
                    multiple=True,
                )
            ),
        }
    )

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_BASE_URL].rstrip("/"))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Meshcore Observer", data=user_input)

        return self.async_show_form(step_id="user", data_schema=_schema({}), errors={})

    @staticmethod
    def async_get_options_flow(config_entry):
        return MeshcoreOptionsFlow(config_entry)

class MeshcoreOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(current))
