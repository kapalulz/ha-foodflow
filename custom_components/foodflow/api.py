"""Read-only client of the FoodFlow Kitchen page (GET /api/ha). It never writes anything."""

from __future__ import annotations

import math
from typing import Any
from urllib.parse import urlsplit

import aiohttp

from .const import PATH, SCHEMA_VERSION

TIMEOUT = aiohttp.ClientTimeout(total=30)


def normalize_url(value: str) -> str:
    """The Kitchen origin, e.g. http://192.168.1.10:9290 — no path, query or credentials."""
    url = urlsplit(value.strip())
    if (
        url.scheme not in ("http", "https")
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
        or url.path not in ("", "/")
    ):
        raise ValueError("Use the Kitchen address without a path, credentials or query")
    return value.strip().rstrip("/")


def _dish(d: Any) -> bool:
    return isinstance(d, dict) and isinstance(d.get("name"), str)


def validate(data: Any) -> dict[str, Any]:
    """A malformed answer must not reach the cards."""

    def require(ok: bool) -> None:
        if not ok:
            raise ValueError("Invalid FoodFlow answer")

    try:
        require(isinstance(data, dict) and data["schema_version"] == SCHEMA_VERSION)
        require(data["next"] is None or _dish(data["next"]))
        require(all(_dish(d) for d in data["queue"]) and all(_dish(d) for d in data["extras"]))
        for lst in data["shopping"]:
            require(isinstance(lst["title"], str) and isinstance(lst["items"], list))
        require(isinstance(data["thaw"], list) and isinstance(data["use_up"], list))
        for x in data["use_up"]:
            require(isinstance(x["amount"], int | float) and math.isfinite(x["amount"]))
        for k in data.get("kinds", []):  # newer Kitchen pages: the queue by dish type
            require(isinstance(k["kind"], str) and isinstance(k["label"], str))
            require(k["next"] is None or _dish(k["next"]))
            require(all(_dish(d) for d in k["queue"]))
    except (KeyError, TypeError) as err:
        raise ValueError("Invalid FoodFlow answer") from err
    return data


async def fetch(session: aiohttp.ClientSession, url: str) -> dict[str, Any]:
    async with session.get(
        normalize_url(url) + PATH, timeout=TIMEOUT, allow_redirects=False
    ) as response:
        if response.status == 404:
            raise ValueError("No /api/ha: update FoodFlow")
        response.raise_for_status()
        return validate(await response.json(content_type=None))
