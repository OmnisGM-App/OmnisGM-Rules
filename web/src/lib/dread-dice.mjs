// «Кубы угрозы» (хоумбрю OmnisGM): вероятности и переходы порога для калькулятора на странице
// `src/dnd/homebrew/*/dread-dice.md`. Правила — в самом тексте страницы, раздел «Калькулятор».

/** @typedef {'light' | 'dark'} DieColor */
/** @typedef {'normal' | 'advantage' | 'disadvantage'} RollMode */
/** @typedef {{ color: DieColor, value: number }} Die */
/** @typedef {{ light: number, dark: number }} Bag */
/**
 * @typedef {object} Config
 * @property {number} light        светлых кубов в полном мешке (W)
 * @property {number} dark         тёмных кубов в полном мешке (B)
 * @property {number} base         базовый порог T₀, 0–20
 * @property {number} step         шаг роста Δ, целое ≥ 0
 * @property {boolean} resetWithStep  сброс после события к min(20, T₀ + Δ), а не к T₀
 * @property {boolean} twoDice     преимущество и помеха — двумя кубами из мешка
 * @property {boolean} exhaust     вытянутые кубы не возвращаются до пополнения
 * @property {boolean} pairEffects отмечать пары «оба тёмные» / «оба светлые»
 */
/** @typedef {'light' | 'safe-20' | 'event' | 'growth'} Outcome */

export const MAX_THRESHOLD = 20;

/** Целое в границах; нечисло и дробь — к ближайшему допустимому целому. */
export function clampInt(/** @type {number} */ n, /** @type {number} */ min, /** @type {number} */ max) {
  const v = Number.isFinite(n) ? Math.round(n) : min;
  return Math.min(max, Math.max(min, v));
}

/** Сколько граней d20 опасны при пороге T: результаты 1…T−1. */
export function dangerFaces(/** @type {number} */ threshold) {
  return clampInt(threshold, 0, MAX_THRESHOLD) === 0 ? 0 : clampInt(threshold, 0, MAX_THRESHOLD) - 1;
}

/** Хватает ли мешка на режим «два куба»: иначе преимущество и помеха идут одним кубом. */
export function usesTwoDice(/** @type {Bag} */ bag, /** @type {RollMode} */ mode, /** @type {boolean} */ twoDice) {
  return twoDice && mode !== 'normal' && bag.light + bag.dark >= 2;
}

/**
 * Вероятность события угрозы на следующей проверке при текущем составе мешка.
 * @param {Bag} bag  кубы, которые сейчас в мешке
 * @param {number} threshold текущий порог T
 * @param {RollMode} mode
 * @param {boolean} twoDice режим «два куба» для преимущества и помехи
 * @returns {number} 0…1; пустой мешок — 0
 */
export function eventChance(bag, threshold, mode, twoDice) {
  const w = bag.light;
  const b = bag.dark;
  const total = w + b;
  if (total <= 0 || b <= 0) return 0;
  const n = dangerFaces(threshold);
  const single = n / 20;
  const keepHigh = (n * n) / 400;
  const keepLow = 1 - ((20 - n) * (20 - n)) / 400;
  if (mode === 'normal') return (b / total) * single;
  const sameDie = mode === 'advantage' ? keepHigh : keepLow;
  if (!usesTwoDice(bag, mode, twoDice)) return (b / total) * sameDie;
  const pairs = total * (total - 1);
  const bothDark = (b * (b - 1)) / pairs;
  const mixed = (2 * b * w) / pairs;
  // Разные цвета: тёмный куб остаётся, только если он строго выше (преимущество) или строго ниже
  // (помеха) светлого — ничья уходит светлому.
  const mixedDark = mode === 'advantage'
    ? (n * (n - 1)) / 2 / 400
    : (20 * n - (n * (n + 1)) / 2) / 400;
  return bothDark * sameDie + mixed * mixedDark;
}

/**
 * Какой куб остаётся при преимуществе или помехе; равные числа разного цвета — светлый.
 * @param {Die[]} dice
 * @param {RollMode} mode
 * @returns {number} индекс оставленного куба
 */
export function keptIndex(dice, mode) {
  let best = 0;
  for (let i = 1; i < dice.length; i++) {
    const a = dice[i].value;
    const c = dice[best].value;
    const better = mode === 'disadvantage' ? a < c : a > c;
    if (better || (a === c && dice[i].color === 'light' && dice[best].color === 'dark')) best = i;
  }
  return best;
}

/**
 * Итог проверки для угрозы по оставленному кубу и его финальному числу.
 * @param {Die} die
 * @param {{ threshold: number, base: number, step: number, resetWithStep: boolean }} p
 * @returns {{ outcome: Outcome, threshold: number }}
 */
export function resolveThreat(die, p) {
  const threshold = clampInt(p.threshold, 0, MAX_THRESHOLD);
  if (die.color === 'light') return { outcome: 'light', threshold };
  if (die.value === 20) return { outcome: 'safe-20', threshold };
  if (die.value < threshold) {
    const reset = p.base + (p.resetWithStep ? p.step : 0);
    return { outcome: 'event', threshold: clampInt(reset, 0, MAX_THRESHOLD) };
  }
  return { outcome: 'growth', threshold: clampInt(threshold + p.step, 0, MAX_THRESHOLD) };
}

/** Новый текущий порог при смене T₀: накопленная надбавка сохраняется. */
export function shiftThreshold(/** @type {number} */ threshold, /** @type {number} */ oldBase, /** @type {number} */ newBase) {
  return clampInt(threshold + (newBase - oldBase), 0, MAX_THRESHOLD);
}

/**
 * @typedef {object} LogEntry
 * @property {RollMode} mode
 * @property {Die[]} dice     вытянутые кубы с выпавшими числами; при одном кубе с преимуществом — два броска одного цвета
 * @property {number} kept    индекс оставленного броска в `dice`
 * @property {boolean} manual результат введён вручную
 * @property {boolean} refilled мешок пополнен перед вытягиванием
 * @property {Outcome} outcome
 * @property {number} before  порог до проверки
 * @property {number} after   порог после проверки
 * @property {'both-dark' | 'both-light' | null} pair
 */
/** @typedef {{ config: Config, bag: Bag, threshold: number, log: LogEntry[] }} State */

/** Свежая симуляция: полный мешок, T = T₀. */
export function initialState(/** @type {Config} */ config) {
  return {
    config,
    bag: { light: config.light, dark: config.dark },
    threshold: clampInt(config.base, 0, MAX_THRESHOLD),
    log: [],
  };
}

/** @param {() => number} rng */
const d20 = (rng) => 1 + Math.floor(rng() * 20);

/**
 * Один вытянутый куб из мешка (без возврата внутри одной проверки).
 * @param {Bag} bag
 * @param {() => number} rng
 * @returns {DieColor}
 */
function draw(bag, rng) {
  const color = Math.floor(rng() * (bag.light + bag.dark)) < bag.light ? 'light' : 'dark';
  bag[color] -= 1;
  return color;
}

/**
 * Проверка с мешком: вытянуть, бросить, разрешить угрозу.
 * @param {State} state
 * @param {RollMode} mode
 * @param {() => number} rng случайное число в [0, 1)
 * @returns {State} новое состояние; при полном мешке из нуля кубов — то же самое
 */
export function rollCheck(state, mode, rng) {
  const { config } = state;
  if (config.light + config.dark <= 0) return state;
  let bag = { ...state.bag };
  let refilled = false;
  const needTwo = config.twoDice && mode !== 'normal' && config.light + config.dark >= 2;
  const need = needTwo ? 2 : 1;
  if (bag.light + bag.dark < need) {
    bag = { light: config.light, dark: config.dark };
    refilled = true;
  }
  const pool = { ...bag };
  /** @type {Die[]} */
  let dice;
  if (usesTwoDice(pool, mode, config.twoDice)) {
    dice = [{ color: draw(pool, rng), value: d20(rng) }, { color: draw(pool, rng), value: d20(rng) }];
  } else {
    const color = draw(pool, rng);
    dice = mode === 'normal' ? [{ color, value: d20(rng) }] : [{ color, value: d20(rng) }, { color, value: d20(rng) }];
  }
  const kept = mode === 'normal' ? 0 : keptIndex(dice, mode);
  const res = resolveThreat(dice[kept], { threshold: state.threshold, base: config.base, step: config.step, resetWithStep: config.resetWithStep });
  const twoDrawn = dice.length === 2 && pool.light + pool.dark === bag.light + bag.dark - 2;
  /** @type {LogEntry['pair']} */
  let pair = null;
  if (config.pairEffects && twoDrawn && dice[0].color === dice[1].color) pair = dice[0].color === 'dark' ? 'both-dark' : 'both-light';
  return {
    config,
    bag: config.exhaust ? pool : bag,
    threshold: res.threshold,
    log: [{ mode, dice, kept, manual: false, refilled, outcome: res.outcome, before: state.threshold, after: res.threshold, pair }, ...state.log],
  };
}

/**
 * Результат, брошенный за столом: цвет оставленного куба и его финальное число — после
 * перебросов и замен. Состав мешка не меняется.
 * @param {State} state
 * @param {Die} die
 * @returns {State}
 */
export function recordResult(state, die) {
  const { config } = state;
  const value = clampInt(die.value, 1, 20);
  const res = resolveThreat({ color: die.color, value }, { threshold: state.threshold, base: config.base, step: config.step, resetWithStep: config.resetWithStep });
  return {
    ...state,
    threshold: res.threshold,
    log: [{ mode: 'normal', dice: [{ color: die.color, value }], kept: 0, manual: true, refilled: false, outcome: res.outcome, before: state.threshold, after: res.threshold, pair: null }, ...state.log],
  };
}

/** Мешок снова полон по текущему составу; порог и журнал не меняются. */
export function refill(/** @type {State} */ state) {
  return { ...state, bag: { light: state.config.light, dark: state.config.dark } };
}

/**
 * Новые параметры мастера. Смена T₀ сдвигает текущий T на ту же разницу; смена состава
 * наполняет мешок заново.
 * @param {State} state
 * @param {Config} next
 * @returns {State}
 */
export function reconfigure(state, next) {
  const prev = state.config;
  const bagChanged = prev.light !== next.light || prev.dark !== next.dark || prev.exhaust !== next.exhaust;
  return {
    ...state,
    config: next,
    bag: bagChanged ? { light: next.light, dark: next.dark } : state.bag,
    threshold: prev.base !== next.base ? shiftThreshold(state.threshold, prev.base, next.base) : state.threshold,
  };
}
