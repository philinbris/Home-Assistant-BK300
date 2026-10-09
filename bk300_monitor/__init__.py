"""The BK300 Battery Monitor integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BK300 Battery Monitor from a config entry."""
    # Forward the setup to the sensor platform (sensor.py)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This ensures sensors disconnect cleanly if you delete a module instance
    return await hass.config_entries.async_unload_entry_platforms(entry, PLATFORMS)