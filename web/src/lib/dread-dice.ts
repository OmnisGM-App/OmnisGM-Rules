// «Кубы угрозы» (хоумбрю OmnisGM): шанс события и переходы порога для калькулятора страницы
// src/dnd/homebrew/*/01_DreadDice.md; формулы и поведение описаны в её разделе «Калькулятор».
export type DieColor = 'light' | 'dark';
export type RollMode = 'normal' | 'advantage' | 'disadvantage';
export type Outcome = 'light' | 'safe-20' | 'event' | 'growth';
export interface Die { color: DieColor; value: number }
export interface Bag { light: number; dark: number }
export interface Config extends Bag {
  base: number; step: number; resetWithStep: boolean; twoDice: boolean; exhaust: boolean; pairEffects: boolean;
}
export interface LogEntry {
  mode: RollMode; dice: Die[]; kept: number; manual: boolean; refilled: boolean;
  outcome: Outcome; before: number; after: number; pair: 'both-dark' | 'both-light' | null;
}
export interface State { config: Config; bag: Bag; threshold: number; log: LogEntry[] }
interface ThreatParams { threshold: number; base: number; step: number; resetWithStep: boolean }

export const MAX_THRESHOLD = 20;

export function clampInt(n: number, min: number, max: number) {
  const v = Number.isFinite(n) ? Math.round(n) : min;
  return Math.min(max, Math.max(min, v));
}

export function dangerFaces(threshold: number) {
  return Math.max(0, clampInt(threshold, 0, MAX_THRESHOLD) - 1);
}

export function usesTwoDice(bag: Bag, mode: RollMode, twoDice: boolean) {
  return twoDice && mode !== 'normal' && bag.light + bag.dark >= 2;
}

/** Шанс события на следующей проверке при текущем остатке мешка; пустой мешок — 0. */
export function eventChance(bag: Bag, threshold: number, mode: RollMode, twoDice: boolean) {
  const w = bag.light;
  const b = bag.dark;
  const total = w + b;
  if (total <= 0 || b <= 0) return 0;
  const n = dangerFaces(threshold);
  const keepHigh = (n * n) / 400;
  const keepLow = 1 - ((20 - n) * (20 - n)) / 400;
  if (mode === 'normal') return (b / total) * (n / 20);
  const sameDie = mode === 'advantage' ? keepHigh : keepLow;
  if (!usesTwoDice(bag, mode, twoDice)) return (b / total) * sameDie;
  const pairs = total * (total - 1);
  // Пара разных цветов: ничья уходит светлому, поэтому тёмный должен быть строго выше или ниже.
  const mixedDark = mode === 'advantage' ? (n * (n - 1)) / 2 / 400 : (20 * n - (n * (n + 1)) / 2) / 400;
  return ((b * (b - 1)) / pairs) * sameDie + ((2 * b * w) / pairs) * mixedDark;
}

/** Индекс оставленного куба; равные числа разного цвета — светлый. */
export function keptIndex(dice: Die[], mode: RollMode) {
  let best = 0;
  for (let i = 1; i < dice.length; i++) {
    const a = dice[i].value;
    const c = dice[best].value;
    const better = mode === 'disadvantage' ? a < c : a > c;
    if (better || (a === c && dice[i].color === 'light' && dice[best].color === 'dark')) best = i;
  }
  return best;
}

export function resolveThreat(die: Die, p: ThreatParams): { outcome: Outcome; threshold: number } {
  const threshold = clampInt(p.threshold, 0, MAX_THRESHOLD);
  if (die.color === 'light') return { outcome: 'light', threshold };
  if (die.value === 20) return { outcome: 'safe-20', threshold };
  if (die.value < threshold) {
    return { outcome: 'event', threshold: clampInt(p.base + (p.resetWithStep ? p.step : 0), 0, MAX_THRESHOLD) };
  }
  return { outcome: 'growth', threshold: clampInt(threshold + p.step, 0, MAX_THRESHOLD) };
}

export function shiftThreshold(threshold: number, oldBase: number, newBase: number) {
  return clampInt(threshold + (newBase - oldBase), 0, MAX_THRESHOLD);
}

export function initialState(config: Config): State {
  return { config, bag: { light: config.light, dark: config.dark }, threshold: clampInt(config.base, 0, MAX_THRESHOLD), log: [] };
}

const d20 = (rng: () => number): number => 1 + Math.floor(rng() * 20);

function draw(bag: Bag, rng: () => number): DieColor {
  const color = Math.floor(rng() * (bag.light + bag.dark)) < bag.light ? 'light' : 'dark';
  bag[color] -= 1;
  return color;
}

/** Проверка с мешком; при составе из нуля кубов состояние не меняется. */
export function rollCheck(state: State, mode: RollMode, rng: () => number): State {
  const { config } = state;
  if (config.light + config.dark <= 0) return state;
  let bag = { ...state.bag };
  let refilled = false;
  const need = usesTwoDice(config, mode, config.twoDice) ? 2 : 1;
  if (bag.light + bag.dark < need) {
    bag = { light: config.light, dark: config.dark };
    refilled = true;
  }
  const pool = { ...bag };
  let dice: Die[];
  if (usesTwoDice(pool, mode, config.twoDice)) {
    dice = [{ color: draw(pool, rng), value: d20(rng) }, { color: draw(pool, rng), value: d20(rng) }];
  } else {
    const color = draw(pool, rng);
    dice = mode === 'normal' ? [{ color, value: d20(rng) }] : [{ color, value: d20(rng) }, { color, value: d20(rng) }];
  }
  const kept = mode === 'normal' ? 0 : keptIndex(dice, mode);
  const res = resolveThreat(dice[kept], { threshold: state.threshold, base: config.base, step: config.step, resetWithStep: config.resetWithStep });
  const twoDrawn = pool.light + pool.dark === bag.light + bag.dark - 2;
  const pair = config.pairEffects && twoDrawn && dice[0].color === dice[1].color
    ? (dice[0].color === 'dark' ? 'both-dark' : 'both-light')
    : null;
  return {
    config,
    bag: config.exhaust ? pool : bag,
    threshold: res.threshold,
    log: [{ mode, dice, kept, manual: false, refilled, outcome: res.outcome, before: state.threshold, after: res.threshold, pair }, ...state.log],
  };
}

/** Результат, брошенный за столом: цвет оставленного куба и финальное число; мешок не меняется. */
export function recordResult(state: State, die: Die): State {
  const { config } = state;
  const value = clampInt(die.value, 1, 20);
  const res = resolveThreat({ color: die.color, value }, { threshold: state.threshold, base: config.base, step: config.step, resetWithStep: config.resetWithStep });
  return {
    ...state,
    threshold: res.threshold,
    log: [{ mode: 'normal', dice: [{ color: die.color, value }], kept: 0, manual: true, refilled: false, outcome: res.outcome, before: state.threshold, after: res.threshold, pair: null }, ...state.log],
  };
}

export function refill(state: State): State {
  return { ...state, bag: { light: state.config.light, dark: state.config.dark } };
}

/** Смена T₀ сдвигает текущий T на ту же разницу; смена состава наполняет мешок заново. */
export function reconfigure(state: State, next: Config): State {
  const prev = state.config;
  const bagChanged = prev.light !== next.light || prev.dark !== next.dark || prev.exhaust !== next.exhaust;
  return {
    ...state,
    config: next,
    bag: bagChanged ? { light: next.light, dark: next.dark } : state.bag,
    threshold: prev.base !== next.base ? shiftThreshold(state.threshold, prev.base, next.base) : state.threshold,
  };
}
