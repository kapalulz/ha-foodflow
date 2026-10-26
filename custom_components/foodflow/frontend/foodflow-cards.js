/* FoodFlow cards v0.1.0 — Next dish, Dish queue, Shopping, Thaw & use up. One file, no build step,
   no external dependencies; loaded by the foodflow integration. Read-only: cooking, buying and
   eating are still done on the Kitchen page. All text goes through textContent. Every block can
   be switched off with `show_<block>: false` (visual editor: checkboxes). */
const FF_VERSION = '0.1.0';
const FF_TEXT = {
  ru: {
    next: 'Готовим', queue: 'Очередь блюд', shopping: 'Покупки', fresh: 'Разморозить и доесть',
    servings: n => `${n} порц.`, minutes: n => `${n} мин`, kcal: n => `${n} ккал`, protein: n => `белок ${n} г`,
    missing: 'Не хватает', ingredients: 'Ингредиенты', steps: 'Приготовление', nothingNext: 'Очередь пуста — автопилот добавит блюда ночью',
    extras: 'Десерт и завтрак', more: n => `ещё ${n}`, emptyShopping: 'Покупать ничего не нужно',
    ranOut: 'кончилось', thaw: 'Разморозить заранее', useUp: 'Скоро испортится', until: d => `до ${d}`, tryRecipe: 'можно приготовить',
    allFresh: 'Размораживать и доедать нечего', today: 'сегодня', tomorrow: 'завтра', receipts: n => `Вопросы по чекам: ${n} — ответьте на «Кухне»`,
    missingSensor: 'Датчик не найден', multiple: 'Несколько датчиков — выберите Entity в настройках',
    noSensor: 'Нет датчика FoodFlow — добавьте интеграцию FoodFlow', unavailable: 'FoodFlow недоступен',
  },
  en: {
    next: 'Cooking next', queue: 'Dish queue', shopping: 'Shopping', fresh: 'Thaw & use up',
    servings: n => `${n} servings`, minutes: n => `${n} min`, kcal: n => `${n} kcal`, protein: n => `protein ${n} g`,
    missing: 'Missing', ingredients: 'Ingredients', steps: 'Steps', nothingNext: 'The queue is empty — the nightly run adds dishes',
    extras: 'Dessert & breakfast', more: n => `${n} more`, emptyShopping: 'Nothing to buy',
    ranOut: 'ran out', thaw: 'Thaw in advance', useUp: 'Spoils soon', until: d => `until ${d}`, tryRecipe: 'try',
    allFresh: 'Nothing to thaw or use up', today: 'today', tomorrow: 'tomorrow', receipts: n => `Receipt questions: ${n} — answer on the Kitchen page`,
    missingSensor: 'Sensor not found', multiple: 'Multiple sensors — select an Entity in settings',
    noSensor: 'No FoodFlow sensor — add the FoodFlow integration', unavailable: 'FoodFlow unavailable',
  },
};
const FF_CSS = `
  :host{display:block;height:100%;container-type:inline-size}
  ha-card{display:block;box-sizing:border-box;height:100%;overflow:auto;padding:20px;color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family,sans-serif)}
  h2{font-size:20px;font-weight:600;margin:0 0 14px;letter-spacing:-.3px}
  h3{font-size:13px;font-weight:600;color:var(--secondary-text-color);margin:14px 0 6px;text-transform:none}
  .muted{color:var(--secondary-text-color);font-size:12px}.empty{padding:12px 0;color:var(--secondary-text-color)}
  .row{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin:6px 0;font-size:14px}
  .row b{font-weight:600;font-variant-numeric:tabular-nums;white-space:nowrap}
  .chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}.chip{font-size:12px;padding:3px 8px;border-radius:12px;background:var(--secondary-background-color,#eee)}
  .warn{color:var(--error-color,#db4437)}.ok{color:var(--success-color,#43a047)}
  .alert{background:color-mix(in srgb,var(--warning-color,#ffa000) 16%,transparent);border-radius:8px;padding:8px 10px;font-size:13px;margin:8px 0}
  details{margin-top:10px}summary{cursor:pointer;font-weight:600;font-size:14px;padding:4px 0}
  summary:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px;border-radius:4px}
  ul,ol{margin:6px 0;padding-left:20px}li{margin:4px 0;font-size:14px;line-height:1.45}
  li.no{color:var(--error-color,#db4437)}
  @container(max-width:330px){ha-card{padding:14px}h2{font-size:18px}}`;

/** Common part: config, sensor lookup by foodflow_metric, error states, `show_*` switches. */
class FoodFlowCard extends HTMLElement {
  static metric = '';
  static blocks = [];  // [key, ru, en]
  constructor() { super(); this.attachShadow({ mode: 'open' }); }
  setConfig(config) {
    if (config.entity != null && typeof config.entity !== 'string') throw new Error('entity must be an Entity ID string');
    if (config.language && !['ru', 'en'].includes(config.language)) throw new Error('language: ru | en');
    this.check(config);
    this._config = { ...config, entity: typeof config.entity === 'string' ? config.entity.trim() : '' };
    this.render();
  }
  check() {}
  set hass(hass) {
    const previous = this._hass; this._hass = hass;
    if (!previous || previous.states !== hass.states || previous.language !== hass.language) this.render();
  }
  static getConfigElement() { const el = document.createElement('foodflow-card-editor'); el.card = this; return el; }
  static getStubConfig() { return {}; }
  getCardSize() { return 4; }
  getGridOptions() { return { columns: 12, min_columns: 6, rows: 4, min_rows: 2 }; }
  show(key) { return this._config[`show_${key}`] !== false; }
  el(tag, text, cls, parent) {
    const n = document.createElement(tag);
    if (text != null) n.textContent = text;
    if (cls) n.className = cls;
    if (parent) parent.append(n);
    return n;
  }
  day(iso) {
    if (!iso) return '';
    const today = this._today;
    const t = new Date(`${today}T12:00:00`); t.setDate(t.getDate() + 1);
    if (iso === today) return this.t.today;
    if (iso === t.toISOString().slice(0, 10)) return this.t.tomorrow;
    return this.dayFmt.format(new Date(`${iso}T12:00:00`)).replace('.', '');
  }
  amount(x) { return x.amount == null ? '' : `${this.num.format(x.amount)} ${x.unit || ''}`.trim(); }
  render() {
    if (!this._config || !this._hass) return;
    const lang = this._config.language || (this._hass.language?.startsWith('ru') ? 'ru' : 'en');
    const t = this.t = FF_TEXT[lang];
    this.num = new Intl.NumberFormat(lang === 'ru' ? 'ru-RU' : 'en-US', { maximumFractionDigits: 1 });
    this.dayFmt = new Intl.DateTimeFormat(lang === 'ru' ? 'ru-RU' : 'en-US', { day: 'numeric', month: 'short' });
    const root = this.shadowRoot; root.replaceChildren();
    this.el('style', FF_CSS + this.css(), null, root);
    const card = this.el('ha-card', null, this.constructor.metric, root);
    if (this.show('title')) this.el('h2', this._config.title || t[this.constructor.metric], null, card);
    const states = this._hass.states;
    let id = this._config.entity, state = id ? states[id] : null, multiple = false;
    if (!id) {
      const ids = Object.keys(states).filter(k => k.startsWith('sensor.') && states[k].attributes?.foodflow_metric === this.constructor.metric);
      if (ids.length === 1) [id, state] = [ids[0], states[ids[0]]]; else multiple = ids.length > 1;
    }
    if (!state) { this.el('div', multiple ? t.multiple : id ? `${t.missingSensor}: ${id}` : t.noSensor, 'empty', card); return; }
    if (['unavailable', 'unknown'].includes(state.state) && this.constructor.metric !== 'next') { this.el('div', t.unavailable, 'empty', card); return; }
    if (state.state === 'unavailable') { this.el('div', t.unavailable, 'empty', card); return; }
    this._today = state.attributes.today;
    this.body(card, state.attributes.data, t, state);
  }
  css() { return ''; }
}

/* 1. Next dish: what to cook, how long, what is missing, ingredients and steps. */
class FoodFlowNextCard extends FoodFlowCard {
  static metric = 'next';
  static blocks = [['title', 'Заголовок', 'Title'], ['kind', 'Тип блюда', 'Dish type'],
    ['facts', 'Порции, время, ккал, белок', 'Servings, time, kcal, protein'], ['missing', 'Чего не хватает', 'Missing products'],
    ['ingredients', 'Ингредиенты', 'Ingredients'], ['steps', 'Приготовление', 'Steps']];
  getCardSize() { return 6; }
  getGridOptions() { return { columns: 12, min_columns: 6, rows: 6, min_rows: 2 }; }
  css() { return `.name{font-size:24px;font-weight:650;letter-spacing:-.4px;line-height:1.2}.kind{margin-bottom:2px}`; }
  body(card, d, t) {
    if (!d) { this.el('div', t.nothingNext, 'empty', card); return; }
    if (this.show('kind')) this.el('div', d.kind_label, 'muted kind', card);
    this.el('div', d.name, 'name', card);
    if (this.show('facts')) {
      const chips = this.el('div', null, 'chips', card);
      for (const [v, f] of [[d.servings, t.servings], [d.minutes, t.minutes], [d.kcal, t.kcal], [d.protein, t.protein]])
        if (v) this.el('span', f(this.num.format(v)), 'chip', chips);
    }
    if (this.show('missing') && d.missing?.length) this.el('div', `${t.missing}: ${d.missing.join(', ')}`, 'alert', card);
    if (this.show('ingredients') && d.ingredients?.length) {
      const box = this.el('details', null, null, card); box.open = this._config.open_ingredients !== false;
      this.el('summary', t.ingredients, null, box);
      const ul = this.el('ul', null, null, box);
      for (const i of d.ingredients) this.el('li', [i.name, this.amount(i)].filter(Boolean).join(' — '), i.ok ? '' : 'no', ul);
    }
    if (this.show('steps') && d.steps?.length) {
      const box = this.el('details', null, null, card); box.open = this._config.open_steps === true;
      this.el('summary', t.steps, null, box);
      const ol = this.el('ol', null, null, box);
      for (const s of d.steps) this.el('li', s, null, ol);
    }
  }
}

/* 2. The dish queue: what comes after, with dessert and breakfast. */
class FoodFlowQueueCard extends FoodFlowCard {
  static metric = 'queue';
  static blocks = [['title', 'Заголовок', 'Title'], ['next', 'Первое блюдо (уже на карточке «Готовим»)', 'The first dish (shown on "Cooking next")'],
    ['meta', 'Тип, порции, время', 'Type, servings, time'], ['missing', 'Чего не хватает', 'Missing products'], ['extras', 'Десерт и завтрак', 'Dessert & breakfast']];
  check(config) { if (config.max != null && !(Number(config.max) >= 1)) throw new Error('max: a number from 1'); }
  list(card, dishes, t) {
    const max = Number(this._config.max) || 0;
    const shown = max ? dishes.slice(0, max) : dishes;
    for (const d of shown) {
      const row = this.el('div', null, 'row', card);
      const left = this.el('span', d.name, null, row);
      if (this.show('missing') && d.missing?.length) { left.classList.add('warn'); left.title = `${t.missing}: ${d.missing.join(', ')}`; }
      if (this.show('meta')) this.el('span', [d.kind_label, d.servings && t.servings(this.num.format(d.servings)), d.minutes && t.minutes(d.minutes)].filter(Boolean).join(' · '), 'muted', row);
    }
    if (shown.length < dishes.length) this.el('div', t.more(dishes.length - shown.length), 'muted', card);
  }
  body(card, d, t) {
    const queue = this.show('next') ? d.queue : d.queue.slice(1);
    if (!queue.length && !(this.show('extras') && d.extras.length)) { this.el('div', t.nothingNext, 'empty', card); return; }
    this.list(card, queue, t);
    if (this.show('extras') && d.extras.length) { this.el('h3', t.extras, null, card); this.list(card, d.extras, t); }
  }
}

/* 3. Shopping lists: "buy now" and the later trips. Ticking stays on the Kitchen page. */
class FoodFlowShoppingCard extends FoodFlowCard {
  static metric = 'shopping';
  static blocks = [['title', 'Заголовок', 'Title'], ['later', 'Отложенные списки («Покупки ДД.ММ»)', 'Later trips ("Покупки DD.MM")'],
    ['labels', 'Для каких блюд', 'Which dishes need it'], ['counts', 'Число позиций', 'Item counts']];
  body(card, d, t) {
    const lists = d.lists.filter((l, i) => i === 0 || this.show('later'));
    const total = lists.reduce((n, l) => n + l.items.length, 0);
    if (!total) { this.el('div', t.emptyShopping, 'empty', card); return; }
    for (const l of lists) {
      if (!l.items.length) continue;
      this.el('h3', this.show('counts') ? `${l.title} · ${l.items.length}` : l.title, null, card);
      const ul = this.el('ul', null, null, card);
      for (const i of l.items) {
        const li = this.el('li', i.name, null, ul);
        if (this.show('labels') && i.label) this.el('span', ` — ${i.manual ? t.ranOut : i.label}`, 'muted', li);
      }
    }
  }
}

/* 4. Thaw in advance and food that spoils soon. */
class FoodFlowFreshCard extends FoodFlowCard {
  static metric = 'fresh';
  static blocks = [['title', 'Заголовок', 'Title'], ['thaw', 'Разморозить заранее', 'Thaw in advance'],
    ['use_up', 'Скоро испортится', 'Spoils soon'], ['recipes', 'Что приготовить', 'What to cook'], ['receipts', 'Вопросы по чекам', 'Receipt questions']];
  body(card, d, t, state) {
    const thaw = this.show('thaw') ? d.thaw : [], use = this.show('use_up') ? d.use_up : [];
    const questions = state.attributes.receipt_questions || 0;
    if (this.show('receipts') && questions) this.el('div', t.receipts(questions), 'alert', card);
    if (!thaw.length && !use.length) { this.el('div', t.allFresh, 'empty', card); return; }
    if (thaw.length) {
      this.el('h3', t.thaw, null, card);
      for (const x of thaw) {
        const row = this.el('div', null, 'row', card);
        this.el('span', `${x.items.map(i => [i.name, this.amount(i)].filter(Boolean).join(' ')).join(', ')}`, null, row);
        this.el('span', `${x.name} · ${this.day(x.day)}`, 'muted', row);
      }
    }
    if (use.length) {
      this.el('h3', t.useUp, null, card);
      for (const x of use) {
        const row = this.el('div', null, 'row', card);
        this.el('span', [x.product, this.amount(x)].filter(Boolean).join(' — '), null, row);
        this.el('span', t.until(this.day(x.best_before)), 'muted warn', row);
        if (this.show('recipes') && x.recipes?.length) this.el('div', `${t.tryRecipe}: ${x.recipes.join(', ')}`, 'muted', card);
      }
    }
  }
}

/** One visual editor for the four cards: entity, title, language, card options, a checkbox per block. */
class FoodFlowCardEditor extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: 'open' }); }
  set hass(hass) { const first = !this._hass; this._hass = hass; if (first) this.render(); }
  setConfig(config) { this._config = { ...config }; this.render(); }
  set(key, value) {
    const config = { ...this._config };
    if (value === undefined || value === '') delete config[key]; else config[key] = value;
    this._config = config;
    this.dispatchEvent(new CustomEvent('config-changed', { detail: { config }, bubbles: true, composed: true }));
  }
  render() {
    if (!this._config || !this.card) return;
    const ru = (this._config.language || this._hass?.language || 'ru').startsWith('ru');
    const L = (r, e) => (ru ? r : e);
    const root = this.shadowRoot; root.replaceChildren();
    const style = document.createElement('style');
    style.textContent = `label{display:block;margin:14px 0;color:var(--primary-text-color)}
      input[type=text],input[type=number],select{display:block;box-sizing:border-box;width:100%;margin-top:8px;padding:12px;font:inherit;color:var(--primary-text-color);background:var(--card-background-color,#fff);border:1px solid var(--divider-color,#aaa);border-radius:6px}
      fieldset{border:1px solid var(--divider-color,#aaa);border-radius:8px;margin:16px 0;padding:8px 12px}legend{padding:0 6px;color:var(--secondary-text-color)}
      label.check{display:flex;align-items:center;gap:10px;margin:8px 0}label.check input{width:18px;height:18px;margin:0}`;
    root.append(style);
    const field = (key, caption, type = 'text', parse = v => v) => {
      const label = document.createElement('label'); label.textContent = caption;
      const input = document.createElement('input'); input.type = type; input.setAttribute('aria-label', caption);
      input.value = this._config[key] ?? '';
      input.addEventListener('change', () => this.set(key, input.value.trim() === '' ? undefined : parse(input.value.trim())));
      label.append(input); root.append(label);
    };
    const select = (key, caption, options, parse = v => v) => {
      const label = document.createElement('label'); label.textContent = caption;
      const input = document.createElement('select'); input.setAttribute('aria-label', caption);
      for (const [v, text] of options) { const o = document.createElement('option'); o.value = v; o.textContent = text; input.append(o); }
      input.value = this._config[key] == null ? '' : String(this._config[key]);
      input.addEventListener('change', () => this.set(key, input.value === '' ? undefined : parse(input.value)));
      label.append(input); root.append(label);
    };
    field('entity', L('Сенсор (пусто — найти автоматически)', 'Entity (leave blank to detect automatically)'));
    field('title', L('Заголовок (необязательно)', 'Title (optional)'));
    select('language', L('Язык', 'Language'), [['', L('Как в Home Assistant', 'Home Assistant language')], ['ru', 'Русский'], ['en', 'English']]);
    const metric = this.card.metric;
    if (metric === 'next') {
      select('open_ingredients', L('Ингредиенты', 'Ingredients'), [['', L('Раскрыты', 'Expanded')], ['false', L('Свёрнуты', 'Collapsed')]], v => v === 'true');
      select('open_steps', L('Приготовление', 'Steps'), [['', L('Свёрнуто', 'Collapsed')], ['true', L('Раскрыто', 'Expanded')]], v => v === 'true');
    }
    if (metric === 'queue') field('max', L('Сколько блюд показывать (пусто — все)', 'How many dishes (blank — all)'), 'number', Number);
    const box = document.createElement('fieldset'); const lg = document.createElement('legend'); lg.textContent = L('Показывать', 'Show'); box.append(lg);
    for (const [key, r, e] of this.card.blocks) {
      const label = document.createElement('label'); label.className = 'check';
      const input = document.createElement('input'); input.type = 'checkbox'; input.checked = this._config[`show_${key}`] !== false;
      input.setAttribute('aria-label', L(r, e));
      input.addEventListener('change', () => this.set(`show_${key}`, input.checked ? undefined : false));
      label.append(input, document.createTextNode(L(r, e))); box.append(label);
    }
    root.append(box);
  }
}

if (!customElements.get('foodflow-card-editor')) customElements.define('foodflow-card-editor', FoodFlowCardEditor);
window.customCards = window.customCards || [];
for (const [tag, cls, name, description] of [
  ['foodflow-next-card', FoodFlowNextCard, 'FoodFlow — Next dish', 'Что готовим: блюдо, чего не хватает, рецепт'],
  ['foodflow-queue-card', FoodFlowQueueCard, 'FoodFlow — Dish queue', 'Очередь блюд, десерт и завтрак'],
  ['foodflow-shopping-card', FoodFlowShoppingCard, 'FoodFlow — Shopping', 'Списки покупок (только просмотр)'],
  ['foodflow-fresh-card', FoodFlowFreshCard, 'FoodFlow — Thaw & use up', 'Разморозить заранее и скоро испортится'],
]) {
  if (!customElements.get(tag)) customElements.define(tag, cls);
  if (!window.customCards.some(c => c.type === tag)) window.customCards.push({ type: tag, name, description, preview: true });
}
console.info(`%cFoodFlow cards ${FF_VERSION}`, 'color:#489b83;font-weight:600');
