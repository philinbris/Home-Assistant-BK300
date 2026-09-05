import asyncio
import logging
import sys
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfElectricPotential
from bleak import BleakClient

_LOGGER = logging.getLogger(__name__)
DOMAIN = "bk300_monitor"

NOTIFY_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"
WRITE_UUID  = "0000fff2-0000-1000-8000-00805f9b34fb"

def calculate_x25_crc(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        ref_byte = int(f"{byte:08b}"[::-1], 2)
        crc ^= (ref_byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    ref_crc = int(f"{crc:016b}"[::-1], 2)
    return ref_crc ^ 0xFFFF

def build_request_packet(interval_ms: int) -> bytes:
    data_to_sign = bytes.fromhex("40400c000501") + interval_ms.to_bytes(2, byteorder='little')
    crc_val = calculate_x25_crc(data_to_sign)
    return data_to_sign + crc_val.to_bytes(2, byteorder='little') + bytes.fromhex("0d0a")

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the sensor platform mapping from config details."""
    config = hass.data[DOMAIN][entry.entry_id]
    mac = config["mac_address"]
    interval = config["interval_ms"]
    
    sensor = BK300VoltageSensor(mac, interval)
    async_add_entities([sensor])
    
    # Launch execution asynchronously so it runs concurrently without locking the main thread
    entry.async_create_background_task(hass, sensor.run_client_loop(), f"bk300_loop_{mac}")

class BK300VoltageSensor(SensorEntity):
    """Representation of a BK300 Battery Monitor Voltage Sensor."""

    def __init__(self, mac_address: str, interval_ms: int) -> None:
        self._mac = mac_address
        self._interval = interval_ms
        self._state = None
        self._received_confirmation = False
        self._is_running = True
        
        # Entity structural definitions
        self._attr_name = f"BK300 Battery Voltage {mac_address.upper()}"
        self._attr_unique_id = f"bk300_{mac_address.replace(':', '').lower()}_voltage"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    def notification_handler(self, sender: int, data: bytearray):
        """Process incoming raw telemetry bytes natively."""
        if not self._received_confirmation:
            if len(data) == 11 and data.startswith(b"$$"):
                self._received_confirmation = True
                return

        if len(data) % 2 == 0 and len(data) > 0:
            for i in range(0, len(data), 2):
                chunk = data[i:i+2]
                if chunk == b"$$" or chunk == b"\r\n":
                    continue
                raw_val = int.from_bytes(chunk, byteorder='little')
                self._state = round(raw_val / 100.0, 2)
                self.async_write_ha_state()

    async def run_client_loop(self):
        """Asynchronous reconnection loop for the Bluetooth client."""
        request_packet = build_request_packet(self._interval)
        
        while self._is_running:
            try:
                _LOGGER.info("Connecting to battery monitor: %s", self._mac)
                async with BleakClient(self._mac) as client:
                    if client.is_connected:
                        self._received_confirmation = False
                        await client.start_notify(NOTIFY_UUID, self.notification_handler)
                        await client.write_gatt_char(WRITE_UUID, request_packet, response=False)
                        
                        # Keep alive while connection remains valid
                        while client.is_connected and self._is_running:
                            await asyncio.sleep(1)
            except Exception as err:
                _LOGGER.error("Bluetooth connection error on device %s: %s", self._mac, err)
            
            if self._is_running:
                _LOGGER.info("Reconnection backup loop sleeping for 10 seconds before retry on %s", self._mac)
                await asyncio.sleep(10)

    async def async_will_remove_from_hass(self) -> None:
        """Kill loops cleanly if integration element is uninstalled."""
        self._is_running = False

