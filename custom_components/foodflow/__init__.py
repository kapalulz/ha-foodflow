"""FoodFlow: what to cook next, the dish queue, shopping lists and food to thaw or use up,
read from the Kitchen page. Home Assistant only shows them; it changes nothing in FoodFlow."""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

import aiohttp
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.loader import async_get_integration

from .api import fetch
from .const import CARDS_URL, DOMAIN, SCAN_MINUTES

PLATFORMS = [Platform.SENSOR]
CARDS_FILE = Path(__file__).parent / "frontend" / "foodflow-cards.js"
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)  # set up from the UI only

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Serve the cards and load them on every dashboard (no manual resource). The version in
    the URL makes browsers fetch the new file after an update."""
    version = str((await async_get_integration(hass, DOMAIN)).version)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARDS_URL, str(CARDS_FILE), cache_headers=False)]
    )
    add_extra_js_url(hass, f"{CARDS_URL}?v={version}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    async def update() -> dict:
        try:
            return await fetch(async_get_clientsession(hass), entry.data["url"])
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"Cannot read the FoodFlow Kitchen page: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        config_entry=entry,
        update_method=update,
        update_interval=timedelta(minutes=SCAN_MINUTES),
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
