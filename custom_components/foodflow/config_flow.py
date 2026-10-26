"""Set up FoodFlow from the UI: only the Kitchen page address (it is on the home network)."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import fetch, normalize_url
from .const import DOMAIN


class FoodFlowConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                url = normalize_url(user_input["url"])
            except ValueError:
                errors["base"] = "invalid_url"
            else:
                await self.async_set_unique_id(url.lower())
                self._abort_if_unique_id_configured()
                try:
                    await fetch(async_get_clientsession(self.hass), url)
                except (aiohttp.ClientError, TimeoutError):
                    errors["base"] = "cannot_connect"
                except ValueError:
                    errors["base"] = "invalid_data"
                else:
                    return self.async_create_entry(title="FoodFlow", data={"url": url})
        default = (user_input or {}).get("url", "http://")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("url", default=default): str}),
            errors=errors,
        )
