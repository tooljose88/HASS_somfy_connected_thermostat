import logging

from homeassistant.components.climate import (
    ClimateEntity,
    PRESET_NONE,
    PRESET_AWAY,
    PRESET_HOME,
    PRESET_SLEEP
)

from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
    CONF_USERNAME,
    CONF_PASSWORD
)
from .constants import DOMAIN
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from . import create_thermostat_api
from somfy_connected_thermostat.models import SetTemperatureCommand, SetHeatingModeCommand, HeatingMode

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Somfy Connected Thermostat from a config entry."""
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]
    # tokens = hass.data.get(DOMAIN, {}).get(config_entry.entry_id, {}).get("tokens")

    session = async_create_clientsession(hass)
    try:
        thermostat_api = await create_thermostat_api(session, username, password)
        hass.data[DOMAIN][config_entry.entry_id] = {
            "api": thermostat_api,
            #"tokens": thermostat_api.auth.tokens
        }

        entities = []

        # Retrieve the list of thermostats from the API
        thermostats = await thermostat_api.get_thermostats()
        for thermostat in thermostats:
            smartphones = await thermostat_api.get_smartphones(thermostat.id)
            entities.append(SomfyThermostatClimateEntity(thermostat_api, thermostat, smartphones[0]))

        # Add the thermostat entities to Home Assistant
        async_add_entities(entities)

        # Set the update interval for the climate entities
        #for entity in entities:
        #    entity.platform.entity_scan_interval = timedelta(seconds=60)

    except Exception as e:
        _LOGGER.error("Error setting up Somfy Connected Thermostat integration: %s", str(e))

    return True


class SomfyThermostatClimateEntity(ClimateEntity):
    """Representation of a Somfy Connected Thermostat."""

    def __init__(self, api, thermostat, smartphones):
        """Initialize the thermostat entity."""
        self._api = api
        self._thermostat = thermostat
        self._smartphones = smartphones
        self._battery_level = None
        self._max_temp = 25.0
        self._min_temp = 8.0
        self._target_temperature_step = 1.0

        self._name = thermostat.name
        self._unique_id = thermostat.id

        self._current_temperature = None
        self._target_temperature = 8.0
        self._hvac_list = [HVACMode.HEAT, HVACMode.OFF]
        self._hvac_mode = HVACMode.OFF
        self._preset_mode = PRESET_NONE
        self._preset_modes = [PRESET_NONE,PRESET_AWAY,PRESET_HOME,PRESET_SLEEP]

    @property
    def name(self):
        """Return the display name of the thermostat."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique ID of the thermostat."""
        return self._unique_id

    @property
    def temperature_unit(self):
        """Return the temperature unit."""
        return UnitOfTemperature.CELSIUS

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.PRESET_MODE
        )

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the target temperature."""
        return self._target_temperature

    @property
    def hvac_mode(self):
        """Return the current HVAC mode."""
        return self._hvac_mode

    @property
    def preset_mode(self):
        """Return the current preset mode."""
        return self._preset_mode

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of supported HVAC modes."""
        return self._hvac_list

    @property
    def preset_modes(self):
        """Return the list of supported preset modes."""
        return self._preset_modes
    
    @property
    def max_temp(self):
        """Return the list of supported preset modes."""
        return self._max_temp
    
    @property
    def min_temp(self):
        """Return the list of supported preset modes."""
        return self._min_temp
    
    @property
    def target_temperature_step(self):
        """Return the list of supported preset modes."""
        return self._target_temperature_step
    
    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        attrs = {}
        if self._battery_level is not None:
            attrs['battery_level'] = self._battery_level
        return attrs

    def convert_string_to_enum(self, string_value):
        try:
            return HeatingMode.__members__[string_value.upper()]
        except KeyError:
            _LOGGER.error("Invalid preset mode: %s", string_value)

    async def async_update(self):
        """Update the thermostat entity."""
        try:
            # Fetch the latest data from the API
            thermostat_info = await self._api.get_thermostat_info(self._thermostat.id, self._smartphones.vendor_id)
            _LOGGER.debug("Thermostat Info: %s", thermostat_info.__dict__)
            # Update the entity attributes
            self._current_temperature = thermostat_info.temperature
            self._target_temperature = thermostat_info.temperature_consigne
            self._battery_level = thermostat_info.battery
            self._preset_mode = PRESET_NONE
            # Set the HVAC mode based on the mode value from the response
            if thermostat_info.mode == HeatingMode.FREEZE.value:
                self._hvac_mode = HVACMode.OFF
            else:
                self._hvac_mode = HVACMode.HEAT
                # Set Preset Mode if is not manual
                if thermostat_info.mode != HeatingMode.MANUAL.value:
                    self._preset_mode = thermostat_info.mode

        except Exception as e:
            _LOGGER.error("Error updating Somfy Connected Thermostat entity: %s", str(e))

    async def async_set_temperature(self, **kwargs):
        """Set the target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            command = SetTemperatureCommand(temperature)
            _LOGGER.debug("Send command Info: %s", command.__dict__)
            await self._api.put_thermostat_command(self._thermostat.id, command)

    async def async_set_hvac_mode(self, hvac_mode):
        """Set the HVAC mode."""
        if hvac_mode == HVACMode.HEAT:
            hvac_mode = HeatingMode.MANUAL
        else:
            hvac_mode = HeatingMode.FREEZE
        command = SetHeatingModeCommand(hvac_mode, self._target_temperature)
        await self._api.put_thermostat_command(self._thermostat.id, command)

    async def async_set_preset_mode(self, preset_mode):
        """Set the preset mode."""
        _LOGGER.debug("Somfy Connected Thermostat preset: %s", repr(preset_mode))
        preset = self.convert_string_to_enum(preset_mode) if preset_mode != PRESET_NONE else HeatingMode.MANUAL
        command = SetHeatingModeCommand(preset, self._target_temperature)
        await self._api.put_thermostat_command(self._thermostat.id, command)
