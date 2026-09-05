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
            # Check if this MAC address is already integrated
            await self.async_set_unique_id(user_input["mac_address"].upper())
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title=f"Battery Monitor ({user_input['mac_address'].upper()})", 
                data=user_input
            )

        DATA_SCHEMA = vol.Schema({
            vol.Required("mac_address"): cv.string,
            vol.Required("interval_ms", default=5000): vol.All(vol.Coerce(int), vol.Range(min=100)),
        })

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
