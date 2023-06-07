import logging

from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
import voluptuous as vol
import re

from .constants import DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass, data):
    """Validate the user input allows us to connect."""
    username = data[CONF_USERNAME]
    password = data[CONF_PASSWORD]

    # Check if the username is a valid email
    if not re.match(r"[^@]+@[^@]+\.[^@]+", username):
        raise InvalidUserName("Invalid email format")

    # Check if the password is empty or null
    if not password:
        raise EmptyPassword("Password cannot be empty")

    # Perform any other necessary validation checks
    # ...

    return data


class SomfyConnectedThermostatFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Somfy Connected Thermostat config flow."""

    async def async_step_user(self, user_input=None):
        """Handle the initial step of the config flow."""
        errors = {}

        if user_input is not None:
            try:
                data = await validate_input(self.hass, user_input)

                # Check if there is an existing configuration with the same credentials.
                if self._is_configuration_exists(data):
                    return self.async_abort(reason="already_configured")

                return self.async_create_entry(title=DOMAIN, data=data)
            except Exception as err:
                _LOGGER.error("Error during configuration flow: %s", str(err))
                errors["base"] = "unknown_error"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    def _is_configuration_exists(self, data):
        """Check if a configuration with the same credentials already exists."""
        existing_entries = self.hass.config_entries.async_entries(DOMAIN)

        for entry in existing_entries:
            if (
                entry.data.get(CONF_USERNAME) == data[CONF_USERNAME]
                and entry.data.get(CONF_PASSWORD) == data[CONF_PASSWORD]
            ):
                return True

        return False


class InvalidUserName(vol.Invalid):
    """Exception raised when the username is invalid."""

class EmptyPassword(vol.Invalid):
    """Exception raised when the password is empty."""

