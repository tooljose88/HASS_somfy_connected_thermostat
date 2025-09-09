import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, Platform
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .constants import DOMAIN
from somfy_connected_thermostat import SomfyConnectedThermostatOAuth, SomfyConnectedThermostatApi

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up the Somfy Connected Thermostat integration."""

    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]

    username = conf[CONF_USERNAME]
    password = conf[CONF_PASSWORD]

    session = async_create_clientsession(hass)

    try:
        thermostat_api = await create_thermostat_api(session, username, password)

        hass.data[DOMAIN] = {"api": thermostat_api}

        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=conf
            )
        )
    except Exception as e:
        _LOGGER.error("Error setting up Somfy Connected Thermostat integration: %s", str(e))

    return True


async def create_thermostat_api(session, username, password): # , tokens = None
    """Create an instance of the thermostat API."""
    auth = SomfyConnectedThermostatOAuth(username, password, session)
    thermostat_api = SomfyConnectedThermostatApi(auth, session)
    # if tokens is not None:
    #     thermostat_api.tokens = tokens
    await thermostat_api.login()

    # Return the thermostat API instance
    return thermostat_api


async def async_setup_entry(hass, entry):
    """Set up Somfy Connected Thermostat from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    session = async_create_clientsession(hass)

    try:
        thermostat_api = await create_thermostat_api(session, username, password)
        _LOGGER.debug("The Somfy Thermostat api: %s", str(thermostat_api))
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        else:
            hass.data[DOMAIN][entry.entry_id] = {
                "api": thermostat_api,
                "tokens": thermostat_api.auth.tokens
            }

        hass.async_create_task(
            hass.config_entries.async_forward_entry_setups(entry, ["climate"])
        )
    except Exception as e:
        _LOGGER.error("Error setting up Somfy Connected Thermostat integration: %s", str(e))

    return True


async def async_unload_entry(hass, entry):
    """Unload a Somfy Connected Thermostat config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "climate")

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
