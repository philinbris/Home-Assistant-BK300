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
    config = entry.data
    options = entry.options
    
    mac = config["mac_address"]
    # Fallback to initial config if options flow hasn't been saved yet
    interval = options.get("interval_ms", config.get("interval_ms", 5000))
    zero_offset = options.get("zero_offset", config.get("zero_offset", 0.0))
    span_multiplier = options.get("span_multiplier", config.get("span_multiplier", 1.0))
    
    sensor = BK300VoltageSensor(mac, interval, zero_offset, span_multiplier)
    async_add_entities([sensor])
    
    # Listen for changes coming from the runtime Options Flow UI
    async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Handle updating runtime parameters without needing a reload."""
        _LOGGER.info("Updating calibration configurations dynamically for %s", mac)
        sensor.update_calibration(
            interval_ms=entry.options.get("interval_ms", sensor._interval),
            zero_offset=entry.options.get("zero_offset", sensor._zero_offset),
            span_multiplier=entry.options.get("span_multiplier", sensor._span_multiplier)
        )

    # Bind the listener to this config entry
    entry.async_on_unload(entry.add_update_listener(async_update_listener))
    
    # Launch background task execution
    entry.async_create_background_task(hass, sensor.run_client_loop(), f"bk300_loop_{mac}")

class BK300VoltageSensor(SensorEntity):
    """Representation of a BK300 Battery Monitor Voltage Sensor."""

    def __init__(self, mac_address: str, interval_ms: int, zero_offset: float, span_multiplier: float) -> None:
        self._mac = mac_address
        self._interval = interval_ms
        self._zero_offset = zero_offset
        self._span_multiplier = span_multiplier
        self._state = None
        self._received_confirmation = False
        self._is_running = True
        self._rebuild_packet_required = False
        
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

    def update_calibration(self, interval_ms: int, zero_offset: float, span_multiplier: float) -> None:
        """Update runtime calibration filters immediately from Options Flow."""
        self._zero_offset = zero_offset
        self._span_multiplier = span_multiplier
        
        if self._interval != interval_ms:
            self._interval = interval_ms
            # Flag that the packet needs to be recreated in the client loop
            self._rebuild_packet_required = True

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
                sensor_voltage = raw_val / 100.0
                
                # Apply runtime linear calibration adjustments 
                adjusted_voltage = (sensor_voltage + self._zero_offset) * self._span_multiplier
                
                self._state = round(adjusted_voltage, 2)
                self.async_write_ha_state()

    async def run_client_loop(self):
        """Asynchronous reconnection loop for the Bluetooth client."""
        request_packet = build_request_packet(self._interval)
        self._rebuild_packet_required = False
        
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
                            # If interval config was changed, push the new packet to Bleak
                            if self._rebuild_packet_required:
                                request_packet = build_request_packet(self._interval)
                                await client.write_gatt_char(WRITE_UUID, request_packet, response=False)
                                self._rebuild_packet_required = False
                                
                            await asyncio.sleep(1)
            except Exception as err:
                _LOGGER.error("Bluetooth connection error on device %s: %s", self._mac, err)
            
            if self._is_running:
                _LOGGER.info("Reconnection backup loop sleeping for 10 seconds before retry on %s", self._mac)
                await asyncio.sleep(10)

    async def async_will_remove_from_hass(self) -> None:
        """Kill loops cleanly if integration element is uninstalled."""
        self._is_running = False

