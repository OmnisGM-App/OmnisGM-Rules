#!/usr/bin/env node
// Генератор картинок сущностей (issue #202): очередь — от JSON API Rules минус уже лежащие webp.
// Текст SRD codex НЕ передаётся — визуальная идея своими словами, не производная лицензионного текста.
// env: KIND (вид из KINDS или auto), COUNT, ONLY=slug1,slug2, CHECK_ONLY=1, DESC_ONLY=1,
//      DUMP_PROMPT=1, PUSH_EACH=1, GIT_BRANCH, API_ROOT.
// Требует: codex CLI + CODEX_HOME, cwebp, git.

import { execFileSync, spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, appendFileSync, readFileSync, statSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { homedir } from 'node:os';

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const API_ROOT = process.env.API_ROOT || resolve(REPO, 'web/src/data/api');
const IMG_ROOT = resolve(REPO, 'web/public/img');
const COUNT = Math.max(1, Number.parseInt(process.env.COUNT || '5', 10) || 5);
const ONLY = (process.env.ONLY || '').split(',').map((s) => s.trim()).filter(Boolean);
const PUSH_EACH = process.env.PUSH_EACH === '1';
const GIT_BRANCH = process.env.GIT_BRANCH || 'images-queue';

// `md` — таблицы из src/*.md для того, чего нет в API; слаг — та же slugify, что parsers/base.py,
// чтобы файлы совпали, когда коллекция появится в API.
/**
 * @type {Record<string, {
 *   dir: string, label: string, prompt: string,
 *   api?: Record<string, string[]>,
 *   versions?: Record<string, string[]>,
 *   md?: Record<string, string[]>,
 * }>}
 */
const KINDS = {
  creatures: {
    dir: 'creatures',
    label: 'существа',
    prompt: 'creatures',
    api: { dnd: ['monsters', 'animals'], daggerheart: ['adversaries'] },
  },
  spells: { dir: 'spells', label: 'заклинания', prompt: 'spells', api: { dnd: ['spells'] } },
  'domain-cards': {
    // Карты доменов — «заклинания» Daggerheart: те же способности, тот же промт-шаблон знака.
    dir: 'domain-cards',
    label: 'карты доменов',
    prompt: 'spells',
    api: { daggerheart: ['domain-cards'] },
  },
  'magic-items': {
    dir: 'magic-items',
    label: 'магические предметы',
    prompt: 'magic-items',
    api: { dnd: ['magic-items'] },
    md: {
      daggerheart: [
        'src/daggerheart/srd-1.0/en/17_Glossary/06_Items.md',
        'src/daggerheart/srd-1.0/en/17_Glossary/07_Consumables.md',
      ],
    },
  },
  // Варианты классовых умений и понятия правил (#380): абстрактные знаки, не предметы и не существа.
  'class-options': { dir: 'class-options', label: 'варианты классовых умений', prompt: 'concepts', api: { dnd: ['class-options'] } },
  // Действия, термины, области воздействия и состояния — одна папка: в 5.1 состояния повторены
  // терминами с теми же слагами, и картинка у одного понятия должна быть одна.
  rules: {
    dir: 'rules',
    label: 'понятия правил',
    prompt: 'concepts',
    api: { dnd: ['actions', 'rules-terms', 'areas-of-effect', 'conditions'] },
    // Страницы терминов есть только у 5.2, компендиум Table — тоже 2024; в 5.1 `rules-terms` к тому же
    // несёт таблицу сокращений (AC, C, Cha.…). Состояния 5.1 со своими страницами — из `conditions`.
    versions: { 'rules-terms': ['srd52'] },
  },
  gear: {
    dir: 'gear',
    label: 'снаряжение',
    prompt: 'magic-items',
    api: { dnd: ['equipment', 'weapons', 'armor'] },
    md: {
      daggerheart: [
        'src/daggerheart/srd-1.0/en/17_Glossary/03_Weapons.md',
        'src/daggerheart/srd-1.0/en/17_Glossary/04_Armor.md',
      ],
      brp: [
        'src/brp/srd-1.0/en/09_Glossary/02_Weapons.md',
        'src/brp/srd-1.0/en/09_Glossary/03_Armor.md',
      ],
    },
  },
};

// Порядок для KIND=auto; полноту сверяет orderProblems() (#291).
const ORDER = ['spells', 'magic-items', 'class-options', 'rules', 'gear', 'domain-cards', 'creatures'];

// Функция, а не падение при импорте: иначе юнит-тест недостижим.
export function orderProblems() {
  const forgotten = Object.keys(KINDS).filter((k) => !ORDER.includes(k));
  const unknown = ORDER.filter((k) => !KINDS[k]);
  if (!forgotten.length && !unknown.length) return null;
  return `ORDER разошёлся с KINDS: нет в порядке — ${forgotten.join(', ') || '—'}; ` +
         `нет среди видов — ${unknown.join(', ') || '—'}`;
}

let KIND = process.env.KIND || 'creatures';
if (KIND !== 'auto' && !KINDS[KIND]) {
  console.error(`Неизвестный KIND="${KIND}". Допустимые: ${Object.keys(KINDS).join(', ')}, auto`);
  process.exit(2);
}

const GEN_DIR = resolve(process.env.CODEX_HOME || resolve(homedir(), '.codex'), 'generated_images');
const EXIT_AUTH = 78; // отдельный код: протухший codex-токен

function summary(/** @type {string} */ md) {
  const f = process.env.GITHUB_STEP_SUMMARY;
  if (f) appendFileSync(f, md + '\n');
  console.log(md);
}

// Держателей токена двое — News-CI и Rules-CI от одного ~/.codex/auth.json: перелогин синкать разом.
const AUTH_FIX = [
  '### ❌ codex auth протух (`refresh_token_reused` / `token_revoked`)',
  'Перелогинься локально (`codex login`) и обнови секрет во ВСЕХ репозиториях-держателях:',
  '```',
  'for r in OmnisGM-App/OmnisGM-News OmnisGM-App/OmnisGM-Rules; do',
  '  gh secret set CODEX_AUTH_JSON --repo $r < ~/.codex/auth.json',
  'done',
  '```',
].join('\n');

function isAuthError(/** @type {any} */ err) {
  const s = `${err?.stdout || ''}${err?.stderr || ''}${err?.message || ''}`;
  return /refresh_token_reused|token_revoked|\b401\b|unauthorized/i.test(s);
}

// ── Шаблоны промтов ────────────────────────────────────────────────────────────

const STYLE_TAIL =
  'The background is a deep charcoal gray, almost black. A subtle violet-purple rim light (#7c3aed) ' +
  'outlines the edges, creating a soft ambient glow. The style is clean, modern digital art with a matte ' +
  'finish — minimalist and sleek, NOT painterly, heavily detailed or cartoonish. The composition is ' +
  'centered and works perfectly as a circular crop. Dark fantasy mood combined with a contemporary UI ' +
  'design aesthetic. No text, no letters, no borders, no decorative frames. High contrast between the ' +
  'subject and the faint glow. Square format, 1024x1024 pixels.';

/** @type {Record<string, (d: string) => string>} */
const PROMPTS = {
  creatures: (d) =>
    `A mysterious dark silhouette portrait of ${d} ` +
    'Shown from the shoulders up (head, shoulders and upper chest, with the hands or a held weapon visible near ' +
    'the chest if relevant), facing slightly to the side, with no visible facial features. Include horns, wings, a ' +
    'tail or spikes ONLY if the description mentions them — never add features that are not described (a person ' +
    'stays an ordinary person). If the creature has a signature colour (a chromatic dragon\'s red/green/blue/black/ ' +
    'white, a metallic dragon\'s warm brass/bronze/copper/gold or cool silver, or fire/frost/poison/radiance), let ' +
    'that ONE colour glow warmly so its hue or metal clearly reads, while the violet rim light stays present. ' +
    `Otherwise keep it violet only. A flat dark silhouette. ${STYLE_TAIL}`,

  spells: (d) =>
    `A minimalist arcane icon representing ${d} ` +
    'The icon is a single clear symbol — an elemental shape, a rune-like glyph or a beam/burst of energy — floating ' +
    'in empty space, with no creature, no hands, no caster and no environment. It reads instantly at small size, ' +
    'like an ability icon in a game UI: one dominant shape, no busy detail, no scene. Let the school\'s energy ' +
    'colour glow through the symbol while the violet rim light stays present; if the spell has no obvious colour, ' +
    `keep it violet only. ${STYLE_TAIL}`,

  concepts: (d) =>
    `A minimalist emblem representing ${d} ` +
    'The emblem is a single clear symbol — a gesture, a stance, a stylised figure in motion or an abstract sign — floating ' +
    'in empty space, with no scene and no environment. It reads instantly at small size, like an ability icon in a game ' +
    'UI: one dominant shape, no busy detail. Any figure is a featureless, fully clothed silhouette. Keep it violet unless the concept has an obvious colour (fire, poison, ' +
    `radiance), then let that ONE colour glow while the violet rim light stays present. ${STYLE_TAIL}`,

  'magic-items': (d) =>
    `A dark silhouette of a single fantasy object: ${d} ` +
    'One object only, shown whole and centered against empty space — no hands, no character, no background scene, ' +
    'no pedestal. The object\'s outline is the subject: a flat dark silhouette with the violet rim light tracing ' +
    'its edges. If the item has a signature material or energy (gold, silver, flame, frost, poison), let that ONE ' +
    `colour glow warmly so the material reads, while the violet rim light stays present. ${STYLE_TAIL}`,
};

// ── Шаг 1: короткая визуальная идея своими словами ─────────────────────────────

/** @type {Record<string, (e: any) => string>} */
const DESCRIBE = {
  creatures: (e) => {
    const hint = [e.size, e.type].filter(Boolean).join(' ');
    return [
      `In ONE short sentence, describe the SILHOUETTE OUTLINE of a fantasy tabletop RPG creature named "${e.name}"${hint ? ` (${hint})` : ''}`,
      'for a faceless dark bust portrait (head, shoulders, upper chest). Give ONLY the outline shapes that define the',
      'silhouette: overall head/body shape, and features like horns, ears, wings, frills, tail, hair/mane, or held',
      'weapon/gear — plus its single signature colour if it has one.',
      'Do NOT mention eyes, teeth, mouth, face, expression, scales, skin, textures, patterns or any interior surface',
      'detail — the portrait is a flat faceless silhouette, not a rendered illustration.',
      'Use real knowledge; if the name is unknown, invent a sensible generic fantasy interpretation — do not refuse.',
      'If the name is a humanoid role (assassin, guard, archer, mage, cultist, knight, bandit, soldier, priest…),',
      'describe an ordinary person/humanoid in fitting gear — NOT a monster, no wings/horns/tail.',
      'Reply with ONLY the one sentence: no preamble, no quotes, no lists, no extra commentary.',
    ].join('\n');
  },

  spells: (e) => {
    const facts = [e.school && `school of ${e.school}`, e.level === 0 ? 'cantrip' : e.level && `level ${e.level}`]
      .filter(Boolean).join(', ');
    return [
      `In ONE short sentence, describe a single ICON that stands for the fantasy tabletop RPG spell "${e.name}"${facts ? ` (${facts})` : ''}.`,
      'Describe it IN YOUR OWN WORDS from what the name and school suggest — do not quote or paraphrase any rulebook text.',
      'Give ONLY the visual: the dominant shape or symbol (an elemental form, a rune-like glyph, a beam, a burst, a',
      'swirl) and its single energy colour. Fire → warm orange, frost → pale cyan, necromancy → sickly green, and so on;',
      'if nothing obvious fits, say it stays violet.',
      'No creature, no caster, no hands, no environment, no scene — the icon floats in empty space.',
      'It must read instantly at small size, so keep it to ONE dominant shape, not a busy composition.',
      'Reply with ONLY the one sentence: no preamble, no quotes, no lists, no extra commentary.',
    ].join('\n');
  },

  concepts: (e) => [
    `In ONE short sentence, describe a single ICON that stands for the fantasy tabletop RPG rule or ability "${e.name}".`,
    'Describe it IN YOUR OWN WORDS from what the name suggests — do not quote or paraphrase any rulebook text.',
    'Give ONLY the visual: one symbol — a gesture, a stance, a silhouette of a figure in motion, or an abstract sign',
    '(an eye, a shield, an arrow, a chain, a spiral) — and its single colour if one is obvious; otherwise it stays violet.',
    'For rest, sleep or unconsciousness use an object or sign (a moon, a campfire, a bedroll, an hourglass), not a',
    'sleeping or lying body: the image model draws such a body bare, and the image filter then drops the picture.',
    'No scene, no environment, no text; the icon floats in empty space and reads at small size.',
    'Reply with ONLY the one sentence: no preamble, no quotes, no lists, no extra commentary.',
  ].join('\n'),

  'magic-items': (e) => {
    const facts = [e.type, e.rarity && `${e.rarity} rarity`].filter(Boolean).join(', ');
    return [
      `In ONE short sentence, describe the SILHOUETTE of the fantasy tabletop RPG magic item "${e.name}"${facts ? ` (${facts})` : ''}.`,
      'Describe it IN YOUR OWN WORDS from what the name and type suggest — do not quote or paraphrase any rulebook text.',
      'Give ONLY the object outline: what kind of object it is (blade, staff, ring, flask, cloak, boots, horn…) and its',
      'defining shape, plus its single signature material or energy colour if it has one (gold, silver, flame, frost).',
      'Exactly ONE object — no hands, no wearer, no background, no pedestal, no pair unless the item itself is a pair',
      '(boots, gloves).',
      'Do NOT mention engravings, inscriptions, runes as text, or any surface detail that would not show in a silhouette.',
      'Reply with ONLY the one sentence: no preamble, no quotes, no lists, no extra commentary.',
    ].join('\n');
  },
};

// ── codex ──────────────────────────────────────────────────────────────────────

function runCodexText(/** @type {string} */ instruction) {
  return execFileSync(
    'codex',
    ['exec', '-C', REPO, '-s', 'read-only', '--skip-git-repo-check', instruction],
    { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], maxBuffer: 32 * 1024 * 1024 },
  );
}

// codex exec подмешивает служебные строки (таймстемпы, «tokens used») — оставляем содержательные.
function describe(/** @type {any} */ entity) {
  const raw = runCodexText(DESCRIBE[KINDS[KIND].prompt](entity));
  const desc = raw
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l && !/^\[|tokens used|^codex\b|^-{3,}|^user\b|^assistant\b/i.test(l))
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (!desc) throw new Error(`пустое описание для ${entity.slug} (ответ codex:\n${raw.slice(-400)})`);
  return desc;
}

// Агент только исполняет: промт готов и подставлен скриптом. Файл не просим сохранять по пути —
// image-tool кладёт его в generated_images/, откуда скрипт заберёт свежий PNG.
function codexInstruction(/** @type {string} */ prompt) {
  return [
    'You are an image-generation executor. Do NOT reason about, research, or describe the subject.',
    'Call the image generation tool exactly once with the following prompt, verbatim and unmodified:',
    '',
    prompt,
    '',
    'Then stop. Do NOT move, copy, rename or resize the generated file.',
  ].join('\n');
}

// Вывод нужен и при успехе: вызов без картинки завершается нулём, и причину (отказ инструмента,
// фильтр) видно только в его тексте.
function runCodex(/** @type {string} */ instruction) {
  const r = spawnSync(
    'codex',
    ['exec', '-C', REPO, '-s', 'workspace-write', '--skip-git-repo-check', instruction],
    { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], maxBuffer: 128 * 1024 * 1024 },
  );
  const out = `${r.stdout || ''}${r.stderr || ''}`;
  if (r.error || r.status !== 0) {
    // Поля как у ошибки execFileSync: по ним isAuthError узнаёт протухший токен.
    throw Object.assign(r.error || new Error(`codex exec завершился с кодом ${r.status}`), {
      stdout: r.stdout, stderr: r.stderr,
    });
  }
  return out;
}

// Хвост ответа codex для лога пропуска: без строк хуков и счётчика токенов, не длиннее `max`.
export function codexTail(/** @type {string} */ raw, max = 800) {
  const text = raw
    .split('\n')
    .map((l) => l.trimEnd())
    .filter((l) => l.trim() && !/^hook: |^tokens used$|^[\d\s]+$/.test(l))
    .join('\n');
  return text.length > max ? `…${text.slice(-max)}` : text;
}

function genPngs() {
  if (!existsSync(GEN_DIR)) return [];
  try {
    return readdirSync(GEN_DIR, { recursive: true })
      .filter((p) => typeof p === 'string' && p.toLowerCase().endsWith('.png'))
      .map((p) => resolve(GEN_DIR, /** @type {string} */ (p)));
  } catch {
    return [];
  }
}

function git(/** @type {string[]} */ args) {
  return execFileSync('git', args, { cwd: REPO, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
}

function commitAndPush(/** @type {string} */ rel, /** @type {string} */ name) {
  git(['add', resolve(REPO, rel)]);
  git(['commit', '-m', `chore(images): ${KINDS[KIND].label} — «${name}» (#202)`]);
  try {
    git(['push', 'origin', `HEAD:${GIT_BRANCH}`]);
  } catch (e) {
    console.error('  push не удался (коммит останется локально, уедет со следующим): ' +
                  `${e instanceof Error ? e.message : e}`);
  }
}

// ── Очередь ────────────────────────────────────────────────────────────────────
// Слаг — формула slugify из `.github/scripts/parsers/base.py`: иначе картинка легла бы под чужим именем.
const slugify = (/** @type {string} */ name) =>
  name
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^\w\s-]/g, ' ')
    .replace(/[-\s]+/g, '-')
    .replace(/^-+|-+$/g, '');

// Источник 1 — коллекции JSON API. EN-срез: промт англоязычный, а слаги в EN и RU одни.
/**
 * @param {Record<string, string[]>|undefined} sources
 * @param {(e: any) => void} add
 * @param {Record<string, string[]>} [versions] коллекция → версии, из которых она берётся
 */
function fromApi(sources, add, versions = {}) {
  for (const [game, resources] of Object.entries(sources || {})) {
    const gameDir = resolve(API_ROOT, game);
    if (!existsSync(gameDir)) continue;
    for (const ver of readdirSync(gameDir)) {
      for (const resource of resources) {
        if (versions[resource] && !versions[resource].includes(ver)) continue;
        const file = resolve(gameDir, ver, 'en', resource, 'all.json');
        if (!existsSync(file)) continue;
        for (const e of JSON.parse(readFileSync(file, 'utf8'))) {
          if (!e.slug) continue;
          add({
            game,
            slug: e.slug,
            name: e.name_en || e.name,
            type: e.type || '',
            size: e.size || '',
            school: e.school || '',
            level: e.level,
            rarity: e.rarity || '',
          });
        }
      }
    }
  }
}

// Источник 2 — markdown-таблицы: первая ячейка — имя, вторая — тип; файлы EN — по ним строится слаг.
/**
 * @param {Record<string, string[]>|undefined} sources
 * @param {(e: any) => void} add
 */
function fromMarkdown(sources, add) {
  for (const [game, files] of Object.entries(sources || {})) {
    for (const rel of files) {
      const abs = resolve(REPO, rel);
      if (!existsSync(abs)) {
        console.error(`  таблица не найдена, пропуск: ${rel}`);
        continue;
      }
      const lines = readFileSync(abs, 'utf8').split('\n');
      let header = true;
      for (const line of lines) {
        const t = line.trim();
        if (!t.startsWith('|')) { header = true; continue; }   // конец блока таблицы
        if (/^\|[\s:-]+\|/.test(t)) continue;                  // строка-разделитель
        if (header) { header = false; continue; }              // строка заголовка колонок
        const cells = t.split('|').slice(1, -1).map((c) => c.trim());
        const name = cells[0];
        if (!name || name === '—' || name === '-') continue;
        add({ game, slug: slugify(name), name, type: cells[1] || '', rarity: '' });
      }
    }
  }
}

function loadQueue(kind = KIND) {
  const { api, md, versions } = KINDS[kind];
  /** @type {Map<string, any>} */
  const bySlug = new Map();
  // Слаг уникален внутри игры; версии и источники дедуплицируем — картинка одна на сущность.
  const add = (/** @type {any} */ e) => { if (e.slug && !bySlug.has(`${e.game}/${e.slug}`)) bySlug.set(`${e.game}/${e.slug}`, e); };
  fromApi(api, add, versions);
  fromMarkdown(md, add);
  return [...bySlug.values()].sort((/** @type {any} */ a, /** @type {any} */ b) => (a.game + a.slug).localeCompare(b.game + b.slug));
}

const relPath = (/** @type {any} */ e, kind = KIND) => `web/public/img/${e.game}/${KINDS[kind].dir}/${e.slug}.webp`;
const hasImage = (/** @type {any} */ e, kind = KIND) => existsSync(resolve(REPO, relPath(e, kind)));

// Выбор вида и сводка прогона — от одной функции остатков, чтобы не разъехались.
function remainingByKind() {
  return ORDER.map((kind) => {
    const all = loadQueue(kind);
    return { kind, total: all.length, left: all.filter((e) => !hasImage(e, kind)).length };
  });
}

// Первый вид с непустой очередью (#291); чистая функция — её проверяет scripts/test_gen_images_kind.mjs.
/**
 * @param {{kind: string, left: number, total: number}[]} rows
 * @returns {string|null}
 */
export function nextKind(rows) {
  const next = rows.find((r) => r.left > 0);
  return next ? next.kind : null;
}

// Пустой список вида = данных нет вовсе: отличает обнулившийся API от «всё готово».
/**
 * @param {{kind: string, left: number, total: number}[]} rows
 * @returns {string[]}
 */
export function emptyKinds(rows) {
  return rows.filter((r) => r.total === 0).map((r) => r.kind);
}

export { ORDER, KINDS };

async function main() {
  const orderProblem = orderProblems();
  if (orderProblem) {
    console.error(orderProblem);
    process.exit(2);
  }
  if (KIND === 'auto') {
    const rows = remainingByKind();
    summary('Очередь по видам: ' +
            rows.map((r) => `${KINDS[r.kind].label} — ${r.left} из ${r.total}`).join(', ') + '.');
    // Ноль у ЛЮБОГО вида, а не у всех: `generate_api.py` при потерянных главах выходит нулём,
    // а markdown-очереди переживают поломку API и маскировали бы её.
    const empty = emptyKinds(rows);
    if (empty.length) {
      summary(`### ❌ Нет данных для видов: ${empty.join(', ')} (искал в ${API_ROOT})\n` +
              'Сгенерируй их перед запуском: `node web/scripts/gen-entity-data.mjs`');
      process.exit(1);
    }
    const picked = nextKind(rows);
    if (!picked) {
      summary('### Все виды закрыты — генерировать нечего. ✅');
      if (process.env.GITHUB_OUTPUT) {
        appendFileSync(process.env.GITHUB_OUTPUT, 'has_work=0\n');
      }
      return;
    }
    KIND = picked;
    summary(`Выбран вид: **${KINDS[KIND].label}** (\`${KIND}\`) — первый с непустой очередью.`);
  }
  const all = loadQueue();
  if (all.length === 0) {
    summary(`### ❌ Очередь пуста: не нашёл данных в ${API_ROOT}\n` +
            'Сгенерируй их перед запуском: `node web/scripts/gen-entity-data.mjs`');
    process.exit(1);
  }

  let queue;
  if (ONLY.length) {
    const bySlug = new Map(all.map((e) => [e.slug, e]));
    queue = ONLY.map((s) => bySlug.get(s)).filter(Boolean);
    const missing = ONLY.filter((s) => !bySlug.has(s));
    summary(`Режим ONLY (${KINDS[KIND].label}): перегенерация **${queue.length}**` +
            `${missing.length ? `, не найдены: ${missing.map((s) => `\`${s}\``).join(', ')}` : ''}.`);
  } else {
    const remaining = all.filter((e) => !hasImage(e));
    queue = remaining.slice(0, COUNT);
    summary(`**${KINDS[KIND].label}**: всего **${all.length}**, с картинкой: **${all.length - remaining.length}**, ` +
            `осталось: **${remaining.length}**, сейчас генерим: **${queue.length}**.`);
  }

  // Дешёвый режим для воркфлоу: посчитать очередь без codex/webp.
  if (process.env.CHECK_ONLY) {
    if (process.env.GITHUB_OUTPUT) {
      appendFileSync(process.env.GITHUB_OUTPUT, `has_work=${queue.length > 0 ? '1' : '0'}\n`);
      // Шаг генерации — ОТДЕЛЬНЫЙ запуск скрипта, поэтому выбранный вид передаём наружу:
      // иначе «auto» второй раз считал бы очередь заново и мог бы выбрать другой вид.
      appendFileSync(process.env.GITHUB_OUTPUT, `kind=${KIND}\n`);
    }
    return;
  }
  if (queue.length === 0) {
    summary('Нечего генерировать — всё уже готово. ✅');
    return;
  }

  const seen = new Set(genPngs());
  /** @type {any[]} */
  const generated = [];
  /** @type {string[]} */
  const failed = [];
  // Итог пишется по ходу: прогон, оборванный по лимиту джобы, до хвоста цикла не доживает.
  summary('\n### Картинки прогона');
  const done = (/** @type {any} */ g) => {
    generated.push(g);
    // Описание — в итог: по нему видно, ЧТО агент понял, ещё до взгляда на картинку.
    summary(`- **${g.name}** (\`${g.slug}.webp\`)\n  - _${g.description}_`);
  };
  const skip = (/** @type {string} */ slug) => {
    failed.push(slug);
    summary(`- ⚠️ \`${slug}\` — пропущен, ретрай в следующем прогоне`);
  };

  for (const e of queue) {
    const rel = relPath(e);
    const abs = resolve(REPO, rel);
    mkdirSync(dirname(abs), { recursive: true });
    console.log(`\n=== ${e.game}/${e.slug} (${e.name}) ===`);
    try {
      const description = describe(e);
      console.log(`  → ${description}`);
      if (process.env.DESC_ONLY) { done({ ...e, description }); continue; }

      const prompt = PROMPTS[KINDS[KIND].prompt](description);
      if (process.env.DUMP_PROMPT) {
        console.log(`\n--- FULL codex image instruction ---\n${codexInstruction(prompt)}\n`);
        continue;
      }
      const answer = runCodex(codexInstruction(prompt));

      const fresh = genPngs().filter((p) => !seen.has(p));
      fresh.forEach((p) => seen.add(p));
      if (fresh.length === 0) {
        console.error(`  codex не сгенерировал PNG — пропуск. Ответ codex:\n${codexTail(answer)}`);
        skip(e.slug);
        continue;
      }
      const newest = fresh.map((p) => ({ p, m: statSync(p).mtimeMs })).sort((a, b) => b.m - a.m)[0].p;
      execFileSync('cwebp', ['-resize', '512', '512', '-q', '82', newest, '-o', abs], { stdio: 'inherit' });
      done({ ...e, description, prompt });
      console.log(`  ✓ ${rel}`);
      if (PUSH_EACH) commitAndPush(rel, e.name);
    } catch (err) {
      // PNG упавшего вызова не должен уйти в картинку следующей сущности.
      genPngs().forEach((p) => seen.add(p));
      if (isAuthError(err)) {
        summary(AUTH_FIX);
        process.exit(EXIT_AUTH);
      }
      const io = /** @type {{ stdout?: string, stderr?: string }} */ (err ?? {});
      const said = codexTail(`${io.stdout || ''}${io.stderr || ''}`);
      console.error(`  ошибка на ${e.slug}: ${err instanceof Error ? err.message : err}${said ? `\n${said}` : ''}`);
      skip(e.slug);
    }
  }

  if (PUSH_EACH && generated.length) {
    try { git(['push', 'origin', `HEAD:${GIT_BRANCH}`]); } catch { /* уже залогировано */ }
  }

  summary(`\n### Сгенерировано: ${generated.length}${failed.length ? `, ошибок: ${failed.length}` : ''}`);

  if (process.env.GITHUB_OUTPUT) {
    appendFileSync(process.env.GITHUB_OUTPUT, `generated_count=${generated.length}\n`);
    appendFileSync(process.env.GITHUB_OUTPUT, `generated_slugs=${generated.map((g) => g.slug).join(',')}\n`);
  }
}

// Модуль импортирует юнит-тест — очередь запускается только при прямом запуске.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((err) => {
    summary(`### ❌ Непредвиденная ошибка\n\`\`\`\n${err?.stack || err}\n\`\`\``);
    process.exit(1);
  });
}
