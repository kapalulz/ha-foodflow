"""Four sensors, one per card. The state is a short headline; the card data is the `data`
attribute, kept out of the recorder: Home Assistant shows the food data but does not store it."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import DOMAIN

PARALLEL_UPDATES = 0


def _items(d: dict) -> int:
    return sum(len(lst["items"]) for lst in d["shopping"])


# key, name, icon, state, data, unit
SENSORS: tuple[tuple[str, str, str, Callable, Callable, str | None], ...] = (
    ("next", "Next dish", "mdi:pot-steam", lambda d: (d["next"] or {}).get("name"),
     lambda d: d["next"], None),
    ("queue", "Dish queue", "mdi:format-list-numbered", lambda d: len(d["queue"]),
     lambda d: {"queue": d["queue"], "extras": d["extras"]}, "dishes"),
    ("shopping", "Shopping", "mdi:cart-outline", _items,
     lambda d: {"lists": d["shopping"]}, "items"),
    ("fresh", "Thaw and use up", "mdi:snowflake-melt", lambda d: len(d["thaw"]) + len(d["use_up"]),
     lambda d: {"thaw": d["thaw"], "use_up": d["use_up"]}, "items"),
)  # fmt: skip


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(FoodFlowSensor(entry.runtime_data, entry, *s) for s in SENSORS)


class FoodFlowSensor(CoordinatorEntity[DataUpdateCoordinator[dict]], SensorEntity):
    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset({"data"})

    def __init__(self, coordinator, entry, key, name, icon, state, data, unit) -> None:
        super().__init__(coordinator)
        self.key, self._state, self._data = key, state, data
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self.entity_id = f"sensor.foodflow_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "FoodFlow",
            "manufacturer": "FoodFlow",
            "model": "Kitchen page",
            "configuration_url": entry.data["url"],
        }

    @property
    def native_value(self) -> Any:
        return self._state(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self.coordinator.data
        return {
            "foodflow_metric": self.key,
            "today": d["today"],
            "generated_at": d["generated_at"],
            "receipt_questions": d.get("receipt_questions", 0),
            "data": self._data(d),
        }
