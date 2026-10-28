// Калькулятор «Кубов угрозы»: формулы шанса сверяются с полным перебором исходов, переходы порога —
// с правилами и примером нарастания страницы src/dnd/homebrew/*/01_DreadDice.md.
import {
  clampInt, bagForCheck, dangerFaces, eventChance, keptIndex, resolveThreat, shiftThreshold, initialState, rollCheck,
  recordResult, refill, reconfigure, usesTwoDice,
} from '../src/lib/dread-dice.ts';

/** @typedef {import('../src/lib/dread-dice.ts').Config} Config */
/** @typedef {import('../src/lib/dread-dice.ts').RollMode} RollMode */
/** @typedef {import('../src/lib/dread-dice.ts').DieColor} DieColor */

let failed = 0;
const eq = (/** @type {unknown} */ actual, /** @type {unknown} */ expected, /** @type {string} */ what) => {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    failed++;
    console.error(`  ✗ ${what}\n      ожидалось ${JSON.stringify(expected)}, получено ${JSON.stringify(actual)}`);
  }
};
const near = (/** @type {number} */ actual, /** @type {number} */ expected, /** @type {string} */ what) => {
  if (!(Math.abs(actual - expected) < 1e-12)) {
    failed++;
    console.error(`  ✗ ${what}\n      ожидалось ${expected}, получено ${actual}`);
  }
};

/** Перебор: все упорядоченные пары кубов из мешка и все 400 пар бросков. Ничья разных цветов — светлый. */
function bruteChance(/** @type {number} */ w, /** @type {number} */ b, /** @type {number} */ t, /** @type {RollMode} */ mode, /** @type {boolean} */ twoDice) {
  /** @type {DieColor[]} */
  const bag = [...Array(w).fill('light'), ...Array(b).fill('dark')];
  const n = bag.length;
  const isEvent = (/** @type {DieColor} */ c, /** @type {number} */ v) => c === 'dark' && v !== 20 && v < t;
  let p = 0;
  if (mode === 'normal' || !twoDice || n < 2) {
    for (const c of bag) {
      for (let x = 1; x <= 20; x++) {
        if (mode === 'normal') { if (isEvent(c, x)) p += 1 / n / 20; continue; }
        for (let y = 1; y <= 20; y++) {
          const v = mode === 'advantage' ? Math.max(x, y) : Math.min(x, y);
          if (isEvent(c, v)) p += 1 / n / 400;
        }
      }
    }
    return p;
  }
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      if (i === j) continue;
      for (let x = 1; x <= 20; x++) {
        for (let y = 1; y <= 20; y++) {
          const tie = x === y;
          const firstKept = tie ? bag[i] === 'light' || bag[j] === 'dark' : (mode === 'advantage') === (x > y);
          const [c, v] = firstKept ? [bag[i], x] : [bag[j], y];
          if (isEvent(c, v)) p += 1 / (n * (n - 1)) / 400;
        }
      }
    }
  }
  return p;
}

eq([clampInt(NaN, 0, 20), clampInt(7.6, 0, 20), clampInt(-1, 0, 20)], [0, 8, 0], 'clampInt: нечисло — к нижней границе, дробь округляется, края зажаты');
eq([0, 1, 5, 20, 25, -3].map(dangerFaces), [0, 0, 4, 19, 19, 0], 'dangerFaces: T=0 и T=1 — ни одной, T=20 — 1…19, края зажаты');

/** @type {RollMode[]} */
const MODES = ['normal', 'advantage', 'disadvantage'];
for (const [w, b] of [[5, 1], [4, 2], [3, 3], [0, 2], [1, 1], [2, 0], [0, 1]]) {
  for (const t of [0, 1, 2, 6, 10, 19, 20]) {
    for (const mode of MODES) {
      for (const two of [false, true]) {
        near(eventChance({ light: w, dark: b }, t, mode, two), bruteChance(w, b, t, mode, two),
          `eventChance W=${w} B=${b} T=${t} ${mode} ${two ? 'два куба' : 'один куб'} = перебор`);
      }
    }
  }
}
near(eventChance({ light: 5, dark: 1 }, 6, 'normal', false), 1 / 6 * 5 / 20, 'одиночный бросок: B/(W+B) × (T−1)/20');
near(eventChance({ light: 5, dark: 1 }, 6, 'advantage', false), 1 / 6 * 25 / 400, 'один куб, преимущество: (T−1)²/400');
near(eventChance({ light: 5, dark: 1 }, 6, 'disadvantage', false), 1 / 6 * (1 - 225 / 400), 'один куб, помеха: 1 − (21−T)²/400');
near(eventChance({ light: 5, dark: 1 }, 6, 'advantage', true), 1 / 3 * 10 / 400, 'два куба, преимущество, ничья — светлому');
near(eventChance({ light: 5, dark: 1 }, 6, 'disadvantage', true), 1 / 3 * 85 / 400, 'два куба, помеха, ничья — светлому');
eq(eventChance({ light: 0, dark: 0 }, 10, 'normal', false), 0, 'пустой мешок — шанс 0, не NaN');
eq(usesTwoDice({ light: 0, dark: 1 }, 'advantage', true), false, 'один куб в мешке — режим двух кубов недоступен');

eq(keptIndex([{ color: 'dark', value: 7 }, { color: 'light', value: 7 }], 'advantage'), 1, 'ничья при преимуществе — светлый (тёмный первым)');
eq(keptIndex([{ color: 'light', value: 7 }, { color: 'dark', value: 7 }], 'advantage'), 0, 'ничья при преимуществе — светлый (светлый первым)');
eq(keptIndex([{ color: 'dark', value: 7 }, { color: 'light', value: 7 }], 'disadvantage'), 1, 'ничья при помехе — светлый');
eq(keptIndex([{ color: 'dark', value: 9 }, { color: 'light', value: 7 }], 'advantage'), 0, 'преимущество — больший');
eq(keptIndex([{ color: 'light', value: 9 }, { color: 'dark', value: 7 }], 'disadvantage'), 1, 'помеха — меньший');

const P = { threshold: 5, base: 5, step: 1, resetWithStep: false };
eq(resolveThreat({ color: 'dark', value: 4 }, P), { outcome: 'event', threshold: 5 }, 'T=5, тёмный 4 — событие, сброс к T₀');
eq(resolveThreat({ color: 'dark', value: 5 }, P), { outcome: 'growth', threshold: 6 }, 'T=5, тёмный 5 — без события, T += Δ');
eq(resolveThreat({ color: 'dark', value: 20 }, { ...P, threshold: 20 }), { outcome: 'safe-20', threshold: 20 }, 'тёмная 20 при T=20 — ни события, ни роста');
eq(resolveThreat({ color: 'dark', value: 20 }, P), { outcome: 'safe-20', threshold: 5 }, 'тёмная 20 — без роста');
eq(resolveThreat({ color: 'light', value: 1 }, P), { outcome: 'light', threshold: 5 }, 'светлая 1 — порог не меняется');
eq(resolveThreat({ color: 'dark', value: 1 }, { threshold: 0, base: 0, step: 0, resetWithStep: false }), { outcome: 'growth', threshold: 0 }, 'T₀=0, Δ=0 — события нет');
eq(resolveThreat({ color: 'dark', value: 1 }, { threshold: 0, base: 0, step: 2, resetWithStep: false }), { outcome: 'growth', threshold: 2 }, 'T₀=0, Δ>0 — рост после безопасного тёмного');
eq(resolveThreat({ color: 'dark', value: 3 }, { threshold: 9, base: 8, step: 2, resetWithStep: false }), { outcome: 'event', threshold: 8 }, 'сброс к актуальному T₀');
eq(resolveThreat({ color: 'dark', value: 3 }, { threshold: 9, base: 8, step: 2, resetWithStep: true }), { outcome: 'event', threshold: 10 }, 'сброс со смещением: T₀ + Δ');
eq(resolveThreat({ color: 'dark', value: 3 }, { threshold: 20, base: 19, step: 3, resetWithStep: true }), { outcome: 'event', threshold: 20 }, 'сброс со смещением не выше 20');
eq(resolveThreat({ color: 'dark', value: 19 }, { threshold: 19, base: 5, step: 3, resetWithStep: false }), { outcome: 'growth', threshold: 20 }, 'рост не выше 20');
eq(shiftThreshold(7, 5, 8), 10, 'смена T₀ 5→8 сохраняет надбавку');
eq(shiftThreshold(3, 5, 0), 0, 'смена T₀ не уводит порог ниже 0');

{
  let t = 5;
  const steps = [['dark', 12, 6], ['light', 2, 6], ['dark', 20, 6], ['dark', 5, 5]];
  for (const [color, value, after] of steps) {
    t = resolveThreat({ color: /** @type {DieColor} */ (color), value: Number(value) }, { threshold: t, base: 5, step: 1, resetWithStep: false }).threshold;
    eq(t, after, `пример нарастания: ${color} ${value} → T=${after}`);
  }
}

/** Генератор из заданной последовательности чисел в [0, 1). */
const seq = (/** @type {number[]} */ xs) => { let i = 0; return () => xs[i++ % xs.length]; };
/** @type {Config} */
const CFG = { light: 1, dark: 1, base: 5, step: 1, resetWithStep: false, twoDice: true, exhaust: false, pairEffects: true };

{
  // Мешок [светлый, тёмный]: 0.6 → тёмный; бросок 0.15 → 4.
  const s = rollCheck(initialState(CFG), 'normal', seq([0.6, 0.15]));
  eq([s.log[0].dice, s.log[0].outcome, s.threshold, s.bag], [[{ color: 'dark', value: 4 }], 'event', 5, { light: 1, dark: 1 }], 'бросок с возвратом: событие, мешок полон');
}
{
  // Два куба: тёмный 7, светлый 7 → при преимуществе остаётся светлый.
  const s = rollCheck(initialState(CFG), 'advantage', seq([0.6, 0.3, 0.0, 0.3]));
  eq([s.log[0].dice.map((d) => d.color), s.log[0].kept, s.log[0].outcome, s.log[0].pair], [['dark', 'light'], 1, 'light', null], 'два куба, ничья 7/7 — светлый, порог не меняется');
}
{
  const s = rollCheck(initialState({ ...CFG, light: 0, dark: 2 }), 'disadvantage', seq([0.0, 0.5, 0.0, 0.9]));
  eq([s.log[0].pair, s.log[0].kept], ['both-dark', 0], 'два тёмных — отмечена пара, помеха берёт меньший');
}
{
  const s = rollCheck(initialState({ ...CFG, pairEffects: false, light: 0, dark: 2 }), 'disadvantage', seq([0.0, 0.5, 0.0, 0.9]));
  eq(s.log[0].pair, null, 'парные эффекты выключены — пара не отмечается');
}
{
  const s = rollCheck(initialState({ ...CFG, twoDice: false }), 'advantage', seq([0.6, 0.15, 0.95]));
  eq([s.log[0].dice, s.log[0].kept, s.log[0].outcome, s.threshold], [[{ color: 'dark', value: 4 }, { color: 'dark', value: 20 }], 1, 'safe-20', 5], 'один куб дважды: один цвет у обоих бросков, 20 — без роста');
}
{
  // Исчерпаемый мешок: два броска уносят оба куба, третий пополняет мешок.
  const ex = { ...CFG, exhaust: true };
  let s = rollCheck(initialState(ex), 'normal', seq([0.6, 0.5]));
  eq(s.bag, { light: 1, dark: 0 }, 'исчерпаемый мешок: тёмный вынут');
  near(eventChance(s.bag, s.threshold, 'normal', ex.twoDice), 0, 'шанс считается по остатку мешка');
  s = rollCheck(s, 'normal', seq([0.1, 0.5]));
  eq(s.bag, { light: 0, dark: 0 }, 'исчерпаемый мешок пуст');
  s = rollCheck(s, 'normal', seq([0.1, 0.5]));
  eq([s.log[0].refilled, s.bag], [true, { light: 0, dark: 1 }], 'пустой мешок пополняется перед вытягиванием');
  s = rollCheck(rollCheck(initialState(ex), 'normal', seq([0.6, 0.5])), 'advantage', seq([0.0, 0.5, 0.0, 0.5]));
  eq([s.log[0].refilled, s.log[0].dice.length, s.bag], [true, 2, { light: 0, dark: 0 }], 'двум кубам не хватает одного — пополнение, вынуты оба');
}
{
  const empty = initialState({ ...CFG, light: 0, dark: 0 });
  eq(rollCheck(empty, 'normal', seq([0.5])), empty, 'состав без кубов — бросок ничего не делает');
}
{
  let s = recordResult(initialState(CFG), { color: 'dark', value: 9 });
  eq([s.threshold, s.log[0].manual, s.bag], [6, true, { light: 1, dark: 1 }], 'ручной ввод: финальное число двигает порог, мешок не трогает');
  s = recordResult(s, { color: 'dark', value: 25 });
  eq([s.log[0].dice[0].value, s.log[0].outcome], [20, 'safe-20'], 'ручной ввод вне 1–20 зажимается');
}
{
  let s = rollCheck(initialState({ ...CFG, exhaust: true }), 'normal', seq([0.6, 0.5]));
  s = refill(s);
  eq(s.bag, { light: 1, dark: 1 }, 'пополнение возвращает полный состав');
  s = reconfigure({ ...s, threshold: 7 }, { ...s.config, base: 8 });
  eq([s.threshold, s.bag], [10, { light: 1, dark: 1 }], 'смена T₀ сдвигает T, мешок не трогает');
  s = reconfigure(s, { ...s.config, dark: 3 });
  eq([s.bag, s.threshold], [{ light: 1, dark: 3 }, 10], 'смена состава наполняет мешок, порог не трогает');
}

{
  const lightPair = rollCheck(initialState({ ...CFG, light: 2, dark: 0 }), 'advantage', seq([0.0, 0.5, 0.0, 0.9]));
  eq(lightPair.log[0].pair, 'both-light', 'два светлых при преимуществе — отмечена пара «оба светлые»');
}
{
  const ex = { ...CFG, light: 1, dark: 1, exhaust: true };
  let s = rollCheck(initialState(ex), 'normal', seq([0.6, 0.5]));
  s = rollCheck(s, 'normal', seq([0.1, 0.5]));
  eq(s.bag, { light: 0, dark: 0 }, 'исчерпаемый мешок 1+1 после двух бросков пуст');
  near(eventChance(bagForCheck({ ...s, threshold: 6 }, 'normal'), 6, 'normal', ex.twoDice), bruteChance(1, 1, 6, 'normal', true),
    'пустой остаток: шанс по полному составу, который вытянет следующая проверка');
  const one = rollCheck(initialState(ex), 'normal', seq([0.6, 0.5]));
  eq(one.bag, { light: 1, dark: 0 }, 'остался один светлый');
  near(eventChance(bagForCheck({ ...one, threshold: 6 }, 'advantage'), 6, 'advantage', ex.twoDice), bruteChance(1, 1, 6, 'advantage', true),
    'один куб при двух кубах: шанс по полному составу');
  near(eventChance(bagForCheck({ ...one, threshold: 6 }, 'normal'), 6, 'normal', ex.twoDice), 0, 'один светлый в остатке при обычной проверке — тянет его, шанс 0');
  const back = reconfigure(one, { ...one.config, exhaust: false });
  eq(back.bag, { light: 1, dark: 1 }, 'выключение исчерпаемого мешка наполняет мешок');
}

if (failed) {
  console.error(`dread-dice: ${failed} ошибок`);
  process.exit(1);
}
console.log('dread-dice: ок');
