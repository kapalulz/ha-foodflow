"""The foodflow integration inside a real Home Assistant, against a recorded /api/ha answer of the
Kitchen page (fictional dishes). Run: pip install -r requirements_test.txt, then pytest here."""

import json
from pathlib import Path

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.foodflow  # noqa: F401  (load ours before the test config dir)

URL = "http://kitchen.example.test:9290"
API = URL + "/api/ha"


@pytest.fixture
def payload():
    return json.loads((Path(__file__).parent / "fixture_api_ha.json").read_text())


async def setup(hass, aioclient_mock, payload):
    aioclient_mock.get(API, json=payload)
    entry = MockConfigEntry(domain="foodflow", data={"url": URL}, unique_id=URL)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_flow_creates_entry(hass, aioclient_mock, payload):
    aioclient_mock.get(API, json=payload)
    r = await hass.config_entries.flow.async_init(
        "foodflow", context={"source": config_entries.SOURCE_USER}
    )
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {"url": URL + "/"})

    assert r["type"] is FlowResultType.CREATE_ENTRY and r["data"] == {"url": URL}


async def test_flow_explains_failures(hass, aioclient_mock):
    for url, kwargs, error in (
        ("http://kitchen.example.test:9290/api", None, "invalid_url"),
        (URL, {"status": 500}, "cannot_connect"),
        (URL, {"status": 404}, "invalid_data"),
        (URL, {"json": {"schema_version": 99}}, "invalid_data"),
    ):
        aioclient_mock.clear_requests()
        if kwargs:
            aioclient_mock.get(API, **kwargs)
        r = await hass.config_entries.flow.async_init(
            "foodflow", context={"source": config_entries.SOURCE_USER}
        )
        r = await hass.config_entries.flow.async_configure(r["flow_id"], {"url": url})
        assert r["errors"] == {"base": error}, (url, kwargs)
        hass.config_entries.flow.async_abort(r["flow_id"])


async def test_sensors(hass, aioclient_mock, payload):
    await setup(hass, aioclient_mock, payload)

    nxt = hass.states.get("sensor.foodflow_next")
    queue = hass.states.get("sensor.foodflow_queue")
    shopping = hass.states.get("sensor.foodflow_shopping")
    fresh = hass.states.get("sensor.foodflow_fresh")

    assert nxt.state == payload["next"]["name"] and nxt.attributes["data"]["steps"]
    assert int(queue.state) == len(payload["queue"])
    assert int(shopping.state) == sum(len(x["items"]) for x in payload["shopping"])
    assert int(fresh.state) == len(payload["thaw"]) + len(payload["use_up"])
    assert fresh.attributes["receipt_questions"] == 1


async def test_card_data_is_not_recorded(hass, aioclient_mock, payload):
    await setup(hass, aioclient_mock, payload)
    from custom_components.foodflow.sensor import FoodFlowSensor

    assert "data" in FoodFlowSensor._unrecorded_attributes


async def test_empty_queue_keeps_the_sensor_available(hass, aioclient_mock, payload):
    payload.update(next=None, queue=[], extras=[])

    await setup(hass, aioclient_mock, payload)

    assert hass.states.get("sensor.foodflow_next").state == "unknown"
    assert hass.states.get("sensor.foodflow_queue").state == "0"


async def test_cards_are_served_and_loaded(hass, hass_client, aioclient_mock, payload):
    from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "http", {})
    await setup(hass, aioclient_mock, payload)

    urls = [u for u in hass.data[DATA_EXTRA_MODULE_URL].urls if "foodflow-cards.js" in u]
    resp = await (await hass_client()).get("/foodflow/foodflow-cards.js")

    assert urls == ["/foodflow/foodflow-cards.js?v=0.2.0"]
    assert resp.status == 200 and "foodflow-next-card" in await resp.text()


async def test_menu_by_dish_type(hass, aioclient_mock, payload):
    await setup(hass, aioclient_mock, payload)

    menu = hass.states.get("sensor.foodflow_menu")
    kinds = menu.attributes["data"]["kinds"]

    assert int(menu.state) == sum(k["count"] for k in payload["kinds"])
    assert [k["kind"] for k in kinds] == ["main", "soup", "side", "breakfast", "dessert", "bake"]
    assert kinds[2]["next"]["name"] == "Винегрет"


async def test_older_kitchen_page_without_kinds(hass, aioclient_mock, payload):
    payload.pop("kinds")

    await setup(hass, aioclient_mock, payload)

    menu = hass.states.get("sensor.foodflow_menu")
    assert menu.state == "unknown" and menu.attributes["data"] == {"kinds": None}
    assert hass.states.get("sensor.foodflow_next").state == payload["next"]["name"]
