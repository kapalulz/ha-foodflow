"""Browser checks of foodflow-cards.js with the recorded /api/ha answer (fictional dishes).
Run: python tests/check_cards.py (needs `pip install playwright` and a Chromium).
Screenshots go to /tmp/foodflow-cards-*.png."""

# ruff: noqa: E501
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
DATA = json.loads((root / "tests/fixture_api_ha.json").read_text())
SENSORS = {
    "next": DATA["next"],
    "queue": {"queue": DATA["queue"], "extras": DATA["extras"]},
    "shopping": {"lists": DATA["shopping"]},
    "fresh": {"thaw": DATA["thaw"], "use_up": DATA["use_up"]},
}
THEMES = {
    "light": "body{background:#f4f5f6;--primary-text-color:#20242a;--secondary-text-color:#69717d;--primary-color:#346d99;--divider-color:#dce0e5;--secondary-background-color:#eef0f3}ha-card{background:#fff;border-radius:16px}",
    "dark": "body{background:#151b24;--primary-text-color:#e9edf4;--secondary-text-color:#9ca8b8;--primary-color:#63b6a4;--divider-color:#3c4858;--secondary-background-color:#2a3442;--error-color:#f28b82}ha-card{background:#202937;border-radius:16px}",
}
CARDS = ["next", "queue", "shopping", "fresh"]
current = {}


def text(key):
    return current["page"].evaluate(f"made.{key}.shadowRoot.textContent")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    errors = []
    for theme, width in (("light", 390), ("dark", 1000)):
        page = current["page"] = browser.new_page(viewport={"width": width, "height": 900})
        errors.clear()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content(
            f"<style>{THEMES[theme]} body{{margin:12px;display:grid;gap:12px}}</style>"
        )
        page.add_script_tag(
            path=str(root / "custom_components/foodflow/frontend/foodflow-cards.js")
        )
        page.evaluate(
            """([sensors, cards, today]) => {
              window.ha = {language: 'ru', states: {}};
              for (const key of cards) ha.states['sensor.foodflow_' + key] = {state: '1', attributes: {foodflow_metric: key, today, receipt_questions: 1, data: sensors[key]}};
              window.made = {};
              for (const key of cards) {
                const card = document.createElement(`foodflow-${key}-card`);
                card.setConfig({}); card.hass = ha; document.body.append(card); made[key] = card;
              }
            }""",
            [SENSORS, CARDS, DATA["today"]],
        )

        for key, needle in (("next", "Курица с рисом"), ("next", "Не хватает: Рис"), ("next", "Обжарить 900 г курицы."),
                            ("queue", "Борщ"), ("queue", "Десерт и завтрак"), ("shopping", "Купить сейчас · 2"),
                            ("shopping", "Соль — кончилось"), ("shopping", "Покупки 30.10"), ("fresh", "Разморозить заранее"),
                            ("fresh", "Шпинат"), ("fresh", "можно приготовить: Омлет"), ("fresh", "Вопросы по чекам: 1")):  # fmt: skip
            assert needle in text(key), (key, needle)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
            "horizontal scroll"
        )
        page.screenshot(path=f"/tmp/foodflow-cards-{theme}.png", full_page=True)
        assert not errors, errors
    # blocks off, max, collapsed recipe, empty states, errors, safe title, editor
    page.evaluate(
        "made.next.setConfig({show_steps: false, show_facts: false, open_ingredients: false}); made.next.hass = ha"
    )
    assert "Приготовление" not in text("next") and not page.evaluate(
        "made.next.shadowRoot.querySelector('details').open"
    )
    page.evaluate(
        "made.queue.setConfig({show_next: false, show_extras: false, max: 1}); made.queue.hass = ha"
    )
    assert (
        "Курица с рисом" not in text("queue")
        and "Борщ" in text("queue")
        and "Десерт" not in text("queue")
    )
    page.evaluate(
        "made.shopping.setConfig({show_later: false, show_labels: false}); made.shopping.hass = ha"
    )
    assert "Покупки 30.10" not in text("shopping") and "кончилось" not in text("shopping")
    page.evaluate(
        "made.fresh.setConfig({show_thaw: false, show_use_up: false, show_receipts: false}); made.fresh.hass = ha"
    )
    assert "Размораживать и доедать нечего" in text("fresh")
    page.evaluate(
        "made.next.hass = {...ha, states: {...ha.states, 'sensor.foodflow_next': {state: 'unknown', attributes: {...ha.states['sensor.foodflow_next'].attributes, data: null}}}}"
    )
    assert "Очередь пуста" in text("next")
    page.evaluate(
        "made.queue.hass = {...ha, states: {...ha.states, 'sensor.foodflow_queue': {state: 'unavailable', attributes: {foodflow_metric: 'queue'}}}}"
    )
    assert "FoodFlow недоступен" in text("queue")
    page.evaluate(
        "made.shopping.hass = {...ha, states: {...ha.states, 'sensor.other': ha.states['sensor.foodflow_shopping']}}"
    )
    assert "Несколько датчиков" in text("shopping")
    page.evaluate(
        "made.fresh.setConfig({language: 'en', title: '<img src=x onerror=alert(1)>'}); made.fresh.hass = ha"
    )
    assert page.evaluate(
        "made.fresh.shadowRoot.querySelectorAll('img').length === 0"
    ) and "Thaw in advance" in text("fresh")
    page.evaluate("""() => {
      window.editor = customElements.get('foodflow-queue-card').getConfigElement();
      editor.hass = ha;
      editor.setConfig({type: 'custom:foodflow-queue-card', grid_options: {columns: 6}});
      editor.addEventListener('config-changed', e => window.changed = e.detail.config);
      document.body.append(editor);
    }""")
    page.get_by_label("Десерт и завтрак", exact=True).uncheck()
    assert page.evaluate("changed.show_extras === false && changed.grid_options.columns === 6")
    page.get_by_label("Сколько блюд показывать (пусто — все)", exact=True).fill("3")
    page.get_by_label("Сколько блюд показывать (пусто — все)", exact=True).press("Tab")
    assert page.evaluate("changed.max === 3")
    assert page.evaluate(
        "window.customCards.filter(c => c.type.startsWith('foodflow-')).length === 4"
    )
    assert not errors, errors
    browser.close()
print(
    "FoodFlow cards checks passed: 4 cards, light/dark, phone/desktop, blocks off, max, collapsed recipe, empty, unavailable, ambiguous, safe title, editor."
)
