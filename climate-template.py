"""Climate platform for IR AC control."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    PLATFORM_SCHEMA,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_NAME,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)

CONF_ACS = "acs"
CONF_TURN_ON = "turn_on"
CONF_TURN_OFF = "turn_off"
CONF_TEMPERATURE = "temperature"
CONF_MODE = "mode"
CONF_FAN_SPEED_UP = "fan_speed_up"
CONF_FAN_SPEED_DOWN = "fan_speed_down"

AC_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_TURN_ON): cv.entity_id,
    vol.Required(CONF_TURN_OFF): cv.entity_id,
    vol.Required(CONF_TEMPERATURE): cv.entity_id,
    vol.Required(CONF_MODE): cv.entity_id,
    vol.Optional(CONF_FAN_SPEED_UP): cv.entity_id,
    vol.Optional(CONF_FAN_SPEED_DOWN): cv.entity_id,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_ACS): vol.All(cv.ensure_list, [AC_SCHEMA]),
})

# Map HA HVACMode to IR select option values
HVAC_TO_IR = {
    HVACMode.AUTO: "Auto",
    HVACMode.COOL: "Cool",
    HVACMode.HEAT: "Heat",
    HVACMode.DRY: "Dry",
    HVACMode.FAN_ONLY: "Fan",
}

IR_TO_HVAC = {v: k for k, v in HVAC_TO_IR.items()}


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up IR climate entities."""
    entities = []
    for ac_config in config[CONF_ACS]:
        entities.append(IRClimateEntity(hass, ac_config))
    async_add_entities(entities)


class IRClimateEntity(ClimateEntity):
    """Climate entity wrapping IR AC buttons/number/select."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 16
    _attr_max_temp = 30
    _attr_target_temperature_step = 1
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.AUTO,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
    ]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _enable_turn_on_off_backwards_compat = False

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize."""
        self._attr_name = config[CONF_NAME]
        self._attr_unique_id = f"ir_climate_{config[CONF_NAME]}"
        self._turn_on_entity = config[CONF_TURN_ON]
        self._turn_off_entity = config[CONF_TURN_OFF]
        self._temperature_entity = config[CONF_TEMPERATURE]
        self._mode_entity = config[CONF_MODE]
        self._fan_up_entity = config.get(CONF_FAN_SPEED_UP)
        self._fan_down_entity = config.get(CONF_FAN_SPEED_DOWN)
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = 26
        self._last_hvac_mode = HVACMode.COOL

    async def async_added_to_hass(self) -> None:
        """Subscribe to state changes of underlying entities."""
        @callback
        def _temp_state_changed(event):
            new_state = event.data.get("new_state")
            if new_state and new_state.state not in ("unknown", "unavailable"):
                try:
                    self._attr_target_temperature = float(new_state.state)
                    self.async_write_ha_state()
                except ValueError:
                    pass

        @callback
        def _mode_state_changed(event):
            new_state = event.data.get("new_state")
            if new_state and new_state.state not in ("unknown", "unavailable"):
                hvac_mode = IR_TO_HVAC.get(new_state.state)
                if hvac_mode:
                    self._attr_hvac_mode = hvac_mode
                    self._last_hvac_mode = hvac_mode
                    self.async_write_ha_state()

        async_track_state_change_event(
            self.hass, [self._temperature_entity], _temp_state_changed
        )
        async_track_state_change_event(
            self.hass, [self._mode_entity], _mode_state_changed
        )

        # Sync initial state from underlying entities
        temp_state = self.hass.states.get(self._temperature_entity)
        if temp_state and temp_state.state not in ("unknown", "unavailable"):
            try:
                self._attr_target_temperature = float(temp_state.state)
            except ValueError:
                pass

        mode_state = self.hass.states.get(self._mode_entity)
        if mode_state and mode_state.state not in ("unknown", "unavailable"):
            hvac_mode = IR_TO_HVAC.get(mode_state.state)
            if hvac_mode:
                self._attr_hvac_mode = hvac_mode
                self._last_hvac_mode = hvac_mode

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
            return

        # Turn on first if currently off
        if self._attr_hvac_mode == HVACMode.OFF:
            await self.hass.services.async_call(
                "button", "press",
                {ATTR_ENTITY_ID: self._turn_on_entity},
                blocking=True,
            )

        ir_mode = HVAC_TO_IR.get(hvac_mode)
        if ir_mode:
            await self.hass.services.async_call(
                "select", "select_option",
                {ATTR_ENTITY_ID: self._mode_entity, "option": ir_mode},
                blocking=True,
            )

        self._attr_hvac_mode = hvac_mode
        self._last_hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            return

        temperature = int(temperature)

        # Turn on if currently off
        if self._attr_hvac_mode == HVACMode.OFF:
            await self.hass.services.async_call(
                "button", "press",
                {ATTR_ENTITY_ID: self._turn_on_entity},
                blocking=True,
            )
            self._attr_hvac_mode = self._last_hvac_mode

        await self.hass.services.async_call(
            "number", "set_value",
            {ATTR_ENTITY_ID: self._temperature_entity, "value": temperature},
            blocking=True,
        )

        self._attr_target_temperature = temperature
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn on."""
        await self.hass.services.async_call(
            "button", "press",
            {ATTR_ENTITY_ID: self._turn_on_entity},
            blocking=True,
        )
        self._attr_hvac_mode = self._last_hvac_mode
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Turn off."""
        await self.hass.services.async_call(
            "button", "press",
            {ATTR_ENTITY_ID: self._turn_off_entity},
            blocking=True,
        )
        self._attr_hvac_mode = HVACMode.OFF
        self.async_write_ha_state()
