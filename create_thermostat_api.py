from somfy_connected_thermostat import SomfyAuthentication, SomfyThermostatAPI

async def create_thermostat_api(session, username, password):
    """Create an instance of the thermostat API."""
    auth = SomfyAuthentication(session)
    await auth.login(username, password)
    thermostat_api = SomfyThermostatAPI(session, auth)

    # Return the thermostat API instance
    return thermostat_api