from homeassistant.helpers import config_entry_flow

config_entry_flow.register_discovery_flow(
    "config_editor", "Config Editor", lambda hass: True
)
