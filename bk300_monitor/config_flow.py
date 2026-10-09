import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

DOMAIN = "bk300_monitor"

class BK300ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BK300 Battery Monitor."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step where the user enters device details."""
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input["mac_address"].upper())
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title=f"Battery Monitor ({user_input['mac_address'].upper()})", 
                data=user_input
            )

        DATA_SCHEMA = vol.Schema({
            vol.Required("mac_address"): cv.string,
            vol.Required("interval_ms", default=5000): vol.All(vol.Coerce(int), vol.Range(min=100)),
            vol.Required("zero_offset", default=0.0): vol.Coerce(float),
            vol.Required("span_multiplier", default=1.0): vol.All(vol.Coerce(float), vol.Range(min=0.0)),
        })

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return BK300OptionsFlowHandler()  # <-- Make sure this has empty parentheses!


class BK300OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options adjustment for the BK300 Monitor integration."""

    def __init__(self) -> None:
        """Initialize options flow."""
        # Do not accept or pass config_entry here anymore. 
        # Home Assistant populates self.config_entry automatically.

    async def async_step_init(self, user_input=None):
        """Manage the options settings."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Use .get() safely with strict primitive fallback values to prevent Voluptuous UI errors
        current_config = self.config_entry.data or {}
        current_options = self.config_entry.options or {}

        try:
            interval = int(current_options.get("interval_ms", current_config.get("interval_ms", 5000)))
        except (ValueError, TypeError):
            interval = 5000

        try:
            zero_offset = float(current_options.get("zero_offset", current_config.get("zero_offset", 0.0)))
        except (ValueError, TypeError):
            zero_offset = 0.0

        try:
            span_multiplier = float(current_options.get("span_multiplier", current_config.get("span_multiplier", 1.0)))
        except (ValueError, TypeError):
            span_multiplier = 1.0

        OPTIONS_SCHEMA = vol.Schema({
            vol.Required("interval_ms", default=interval): vol.All(vol.Coerce(int), vol.Range(min=100)),
            vol.Required("zero_offset", default=zero_offset): vol.Coerce(float),
            vol.Required("span_multiplier", default=span_multiplier): vol.All(vol.Coerce(float), vol.Range(min=0.0)),
        })

        return self.async_show_form(step_id="init", data_schema=OPTIONS_SCHEMA)
