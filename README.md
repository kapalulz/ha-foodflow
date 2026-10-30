# ha-foodflow

Home Assistant integration for [FoodFlow](https://github.com/kapalulz/FoodFlow) — a home food management
system on top of [Grocy](https://grocy.info). It shows the FoodFlow **Kitchen page** data as four
dashboard cards:

| Card | Shows |
|---|---|
| `custom:foodflow-menu-card` — «Меню» | the six dish types of the Kitchen page (🍲 main, 🥣 soup, 🥗 salad, 🍳 breakfast, 🍰 dessert, 🥖 baking) as icons with counts; a tap shows that type's next dish with its recipe and the rest of its queue |
| `custom:foodflow-dish-card` — one type | one card per category: `kind: side` — the next salad, `kind: dessert` — the next dessert, and so on |
| `custom:foodflow-next-card` — «Готовим» | the next dish: type, servings, time, kcal, protein, what is missing, ingredients (missing ones in red), steps |
| `custom:foodflow-queue-card` — «Очередь блюд» | the dish queue (main dishes and soup), then dessert and breakfast |
| `custom:foodflow-shopping-card` — «Покупки» | «Купить сейчас» and the later trips («Покупки ДД.ММ»), with the dishes each item is for |
| `custom:foodflow-fresh-card` — «Разморозить и доесть» | thaw reminders for today/tomorrow, food that spoils soon and what to cook from it, receipt questions |

Home Assistant **only reads**: cooking, buying, eating and receipts stay on the Kitchen page, and Grocy remains
the single source of truth. The dish and product names come from FoodFlow (in Russian, the household language);
the card labels are Russian or English.

This repository holds only code: no food data, addresses or keys. You enter the Kitchen address in Home Assistant.

> **По-русски, коротко.** Интеграция показывает в Home Assistant данные страницы «Кухня» FoodFlow: что готовим,
> очередь блюд, покупки, что разморозить и доесть. Только просмотр — готовить и отмечать покупки по-прежнему на
> «Кухне». Установка: HACS → ⋮ → Custom repositories → `https://github.com/kapalulz/ha-foodflow`, тип
> Integration → Download → перезапуск HA → «Добавить интеграцию → FoodFlow» → адрес «Кухни».

## How it works

```
Grocy ──► FoodFlow Kitchen page ──GET /api/ha──► this integration ──► 4 sensors ──► 4 cards
```

- `GET /api/ha` on the Kitchen page (FoodFlow `scripts/kitchen.py`, `ha_summary()`) is a read-only snapshot:
  the next dish with its recipe, the queue, shopping lists, thaw and use-up lists, the number of receipt
  questions. No ids, receipts or settings — nothing that lets Home Assistant change anything.
- The integration polls it every 5 minutes. The Kitchen page is meant for the home network (no password);
  Home Assistant must be able to reach it there — no outside access is needed.
- Sensors: `sensor.foodflow_next` (state: the dish name), `sensor.foodflow_queue` (number of dishes),
  `sensor.foodflow_shopping` (number of items), `sensor.foodflow_fresh` (thaw + use-up items),
  `sensor.foodflow_menu` (queued dishes of all types; the queue by dish type for the Menu and Dish cards —
  needs a Kitchen page from 2026-10-30 or newer, older ones show «Обновите FoodFlow» on those two cards). The card data is
  the `data` attribute, **excluded from the recorder**: Home Assistant keeps no history of the food data, only the
  short states. Exclude the four sensors in the `recorder:` settings if even that is unwanted.
- The integration serves `frontend/foodflow-cards.js` and loads it on every dashboard — **no manual resource**.

## Install

1. **FoodFlow**: a version with `GET /api/ha` (2026-10-26 or newer); after updating —
   `docker restart foodflow-kitchen`. Check: `curl -s http://<kitchen address>/api/ha | head -c 300`.
2. **HACS** → ⋮ → **Custom repositories** → `https://github.com/kapalulz/ha-foodflow`, type **Integration** →
   **Add** → find **FoodFlow** → **Download** → restart Home Assistant.
   *Manual alternative:* copy `custom_components/foodflow` to `/config/custom_components/foodflow` and restart.
3. **Settings → Devices & services → Add integration → FoodFlow**: the Kitchen page address without a path,
   e.g. `http://192.168.1.10:9290` (an address Home Assistant can reach — `localhost` inside HA is HA itself).
   The connection is checked before saving.
4. Refresh the browser. **Edit dashboard → Add card** → «FoodFlow — Menu / Dish / Next dish / Dish queue /
   Shopping / Thaw & use up».

After an update: HACS → Update → restart Home Assistant → refresh the page.

## Card options

Everything is in the **visual editor**: a checkbox per block («Показывать» / "Show"). The same in YAML:

| Option (all cards) | |
|---|---|
| `entity` | the sensor; blank — found automatically (by the `foodflow_metric` attribute) |
| `title` | own title |
| `language` | `ru` / `en`; default — the Home Assistant language |
| `show_title` | `false` — no title |

Any block: `show_<block>: false`.

- **Menu**: `kinds` — which types and in which order, e.g. `[main, side, dessert]` (types: `main`, `soup`,
  `side`, `breakfast`, `dessert`, `bake`); `default_kind` — the one opened first (default: the first type with a
  dish); blocks `counts` (numbers on the icons), `queue` (the rest of the type's queue) and the dish blocks below.
- **Dish**: `kind` — the type (default `main`); blocks `queue` and the dish blocks below. Baking is never queued
  automatically: the card shows the planned bake, or the first of the catalog marked «Не запланировано».
- **Next dish** (also the dish blocks of Menu and Dish): blocks `kind`, `facts`, `missing`, `ingredients`, `steps`; `open_ingredients: false` —
  collapsed ingredients; `open_steps: true` — expanded steps.
- **Dish queue**: blocks `next` (the first dish, already on «Готовим»), `meta`, `missing`, `extras`;
  `max: N` — show N dishes.
- **Shopping**: blocks `later` (the «Покупки ДД.ММ» lists), `labels` (which dishes), `counts`.
- **Thaw & use up**: blocks `thaw`, `use_up`, `recipes`, `receipts`.

Examples:

```yaml
type: custom:foodflow-menu-card
kinds: [main, soup, side, dessert]   # no breakfast, no baking
show_steps: false
```

```yaml
type: custom:foodflow-dish-card
kind: side                 # the next salad
show_queue: false
```

```yaml
type: custom:foodflow-next-card
show_steps: false          # just the dish and the ingredients
```

```yaml
type: custom:foodflow-queue-card
show_next: false           # what comes after the dish on «Готовим»
max: 3
```

```yaml
type: custom:foodflow-shopping-card
show_later: false          # only «Купить сейчас»
```

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest                      # the integration inside a real Home Assistant
python tests/check_cards.py           # the cards in Chromium (pip install playwright)
```

- `tests/test_integration.py` — config flow, errors, sensors, the menu by dish type, an older Kitchen page,
  empty queue, unrecorded card data, card loading.
- `tests/check_cards.py` — all six cards: themes, phone and desktop, icon taps, chosen types, hidden blocks,
  empty and error states, safe title, editor.
- `tests/fixture_api_ha.json` — a recorded `/api/ha` answer with fictional dishes (built by FoodFlow
  `kitchen.ha_summary()` from its unit-test data). If the shape of `/api/ha` changes, regenerate it and keep
  `custom_components/foodflow/api.py` in step; the Kitchen side is tested in FoodFlow
  (`tests/test_home_assistant.py`).
- CI (`.github/workflows/validate.yml`): HACS validation, hassfest, ruff, pytest.
