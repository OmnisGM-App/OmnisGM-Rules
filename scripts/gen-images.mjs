#!/usr/bin/env node
// Генератор картинок сущностей (issue #202). Переехал из Table (scripts/gen-monster-avatars.mjs,
// Table#217) и расширен на заклинания и магические предметы.
//
// Главное отличие от версии в Table: очередь строится ОТ ДАННЫХ RULES, а не от скопированного
// списка имён. Список неизбежно разъезжался с контентом; здесь источник — тот же JSON API, что
// питает страницы, поэтому новая сущность в SRD автоматически попадает в очередь без ручных правок.
//
// Очередь = (сущности коллекции по всем версиям, дедуп по слагу) МИНУС уже лежащие webp.
// Выход — web/public/img/{game}/{dir}/{slug}.webp; раскладка описана
// в documentation/entity-images.md.
//
// Генерация в ДВА шага codex:
//   1) текстом, по имени и паре фактов (школа/тип/редкость) — короткая ВИЗУАЛЬНАЯ идея своими
//      словами. Текст SRD агенту НЕ передаётся: описание должно быть нашим, а не производной
//      лицензионного текста;
//   2) идея вставляется в шаблон промта своего вида (силуэт существа / знак заклинания /
//      силуэт предмета) → image-tool рисует PNG → cwebp -resize 512 512 -q 82.
//
// Каждая готовая картинка коммитится и пушится СРАЗУ (PUSH_EACH=1) — протухший на середине
// токен не теряет уже сгенерённое.
//
// env: KIND (creatures|spells|magic-items), COUNT, ONLY=slug1,slug2, CHECK_ONLY=1, DESC_ONLY=1,
//      DUMP_PROMPT=1, PUSH_EACH=1, GIT_BRANCH, API_ROOT.
// Требует: codex CLI + CODEX_HOME, cwebp, git.

import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, appendFileSync, readFileSync, statSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const API_ROOT = process.env.API_ROOT || resolve(REPO, 'web/src/data/api');
const IMG_ROOT = resolve(REPO, 'web/public/img');
const COUNT = Math.max(1, Number.parseInt(process.env.COUNT || '5', 10) || 5);
const ONLY = (process.env.ONLY || '').split(',').map((s) => s.trim()).filter(Boolean);
const PUSH_EACH = process.env.PUSH_EACH === '1';
const GIT_BRANCH = process.env.GIT_BRANCH || 'images-queue';

// Вид картинки → из каких коллекций API берём очередь и в какую папку кладём.
// Папка существ — общая на игру (слаг живёт в нескольких коллекциях), см. docs/entity-images.md.
const KINDS = {
  creatures: {
    dir: 'creatures',
    label: 'существа',
    sources: { dnd: ['monsters', 'animals'], daggerheart: ['adversaries'] },
  },
  spells: { dir: 'spells', label: 'заклинания', sources: { dnd: ['spells'] } },
  'magic-items': { dir: 'magic-items', label: 'магические предметы', sources: { dnd: ['magic-items'] } },
};

const KIND = process.env.KIND || 'creatures';
if (!KINDS[KIND]) {
  console.error(`Неизвестный KIND="${KIND}". Допустимые: ${Object.keys(KINDS).join(', ')}`);
  process.exit(2);
}

const GEN_DIR = resolve(process.env.CODEX_HOME || resolve(homedir(), '.codex'), 'generated_images');
const EXIT_AUTH = 78; // отдельный код: протухший codex-токен

function summary(md) {
  const f = process.env.GITHUB_STEP_SUMMARY;
  if (f) appendFileSync(f, md + '\n');
  console.log(md);
}

// Держателей токена три (локальный codex → News-CI → Rules-CI) — синкать все разом.
const AUTH_FIX = [
  '### ❌ codex auth протух (`refresh_token_reused` / `token_revoked`)',
  'Перелогинься локально (`codex login`) и обнови секрет во ВСЕХ репозиториях-держателях:',
  '```',
  'for r in OmnisGM-App/OmnisGM-News OmnisGM-App/OmnisGM-Table OmnisGM-App/OmnisGM-Rules; do',
  '  gh secret set CODEX_AUTH_JSON --repo $r < ~/.codex/auth.json',
  'done',
  '```',
].join('\n');

function isAuthError(err) {
  const s = `${err?.stdout || ''}${err?.stderr || ''}${err?.message || ''}`;
  return /refresh_token_reused|token_revoked|\b401\b|unauthorized/i.test(s);
}

// ── Шаблоны промтов ────────────────────────────────────────────────────────────
// Общий скин всех трёх видов: глубокий тёмный фон, фиолетовый rim-light #7c3aed,
// матовая «UI»-эстетика, круговой кроп, без текста и рамок. Различается натура:
// существо — бюст-силуэт, заклинание — знак эффекта, предмет — силуэт объекта.

const STYLE_TAIL =
  'The background is a deep charcoal gray, almost black. A subtle violet-purple rim light (#7c3aed) ' +
  'outlines the edges, creating a soft ambient glow. The style is clean, modern digital art with a matte ' +
  'finish — minimalist and sleek, NOT painterly, heavily detailed or cartoonish. The composition is ' +
  'centered and works perfectly as a circular crop. Dark fantasy mood combined with a contemporary UI ' +
  'design aesthetic. No text, no letters, no borders, no decorative frames. High contrast between the ' +
  'subject and the faint glow. Square format, 1024x1024 pixels.';

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

  'magic-items': (d) =>
    `A dark silhouette of a single fantasy object: ${d} ` +
    'One object only, shown whole and centered against empty space — no hands, no character, no background scene, ' +
    'no pedestal. The object\'s outline is the subject: a flat dark silhouette with the violet rim light tracing ' +
    'its edges. If the item has a signature material or energy (gold, silver, flame, frost, poison), let that ONE ' +
    `colour glow warmly so the material reads, while the violet rim light stays present. ${STYLE_TAIL}`,
};

// ── Шаг 1: короткая визуальная идея своими словами ─────────────────────────────
// Текст SRD агенту НЕ передаётся: он опирается на имя и пару фактов, а описание формулирует
// сам. Так картинка не становится производной лицензионного текста, а промт остаётся коротким.

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

function runCodexText(instruction) {
  return execFileSync(
    'codex',
    ['exec', '-C', REPO, '-s', 'read-only', '--skip-git-repo-check', instruction],
    { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], maxBuffer: 32 * 1024 * 1024 },
  );
}

// codex exec подмешивает служебные строки (таймстемпы, «tokens used») — оставляем содержательные.
function describe(entity) {
  const raw = runCodexText(DESCRIBE[KIND](entity));
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
function codexInstruction(prompt) {
  return [
    'You are an image-generation executor. Do NOT reason about, research, or describe the subject.',
    'Call the image generation tool exactly once with the following prompt, verbatim and unmodified:',
    '',
    prompt,
    '',
    'Then stop. Do NOT move, copy, rename or resize the generated file.',
  ].join('\n');
}

function runCodex(instruction) {
  return execFileSync(
    'codex',
    ['exec', '-C', REPO, '-s', 'workspace-write', '--skip-git-repo-check', instruction],
    { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], maxBuffer: 128 * 1024 * 1024 },
  );
}

function genPngs() {
  if (!existsSync(GEN_DIR)) return [];
  try {
    return readdirSync(GEN_DIR, { recursive: true })
      .filter((p) => typeof p === 'string' && p.toLowerCase().endsWith('.png'))
      .map((p) => resolve(GEN_DIR, p));
  } catch {
    return [];
  }
}

function git(args) {
  return execFileSync('git', args, { cwd: REPO, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
}

function commitAndPush(rel, name) {
  git(['add', resolve(REPO, rel)]);
  git(['commit', '-m', `chore(images): ${KINDS[KIND].label} — «${name}» (#202)`]);
  try {
    git(['push', 'origin', `HEAD:${GIT_BRANCH}`]);
  } catch (e) {
    console.error(`  push не удался (коммит останется локально, уедет со следующим): ${e?.message || e}`);
  }
}

// ── Очередь из данных Rules ────────────────────────────────────────────────────
// EN-срез: имена для промта нужны английские (промт англоязычный), а слаги в EN и RU одни.
function loadQueue() {
  const { sources } = KINDS[KIND];
  const bySlug = new Map();
  for (const [game, resources] of Object.entries(sources)) {
    const gameDir = resolve(API_ROOT, game);
    if (!existsSync(gameDir)) continue;
    for (const ver of readdirSync(gameDir)) {
      for (const resource of resources) {
        const file = resolve(gameDir, ver, 'en', resource, 'all.json');
        if (!existsSync(file)) continue;
        for (const e of JSON.parse(readFileSync(file, 'utf8'))) {
          // Слаг уникален внутри игры; версии дедуплицируем — портрет один на существо.
          if (!e.slug || bySlug.has(`${game}/${e.slug}`)) continue;
          bySlug.set(`${game}/${e.slug}`, {
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
  return [...bySlug.values()].sort((a, b) => (a.game + a.slug).localeCompare(b.game + b.slug));
}

const relPath = (e) => `web/public/img/${e.game}/${KINDS[KIND].dir}/${e.slug}.webp`;
const hasImage = (e) => existsSync(resolve(REPO, relPath(e)));

async function main() {
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
    }
    return;
  }
  if (queue.length === 0) {
    summary('Нечего генерировать — всё уже готово. ✅');
    return;
  }

  const seen = new Set(genPngs());
  const generated = [];
  const failed = [];

  for (const e of queue) {
    const rel = relPath(e);
    const abs = resolve(REPO, rel);
    mkdirSync(dirname(abs), { recursive: true });
    console.log(`\n=== ${e.game}/${e.slug} (${e.name}) ===`);
    try {
      const description = describe(e);
      console.log(`  → ${description}`);
      if (process.env.DESC_ONLY) { generated.push({ ...e, description }); continue; }

      const prompt = PROMPTS[KIND](description);
      if (process.env.DUMP_PROMPT) {
        console.log(`\n--- FULL codex image instruction ---\n${codexInstruction(prompt)}\n`);
        continue;
      }
      runCodex(codexInstruction(prompt));

      const fresh = genPngs().filter((p) => !seen.has(p));
      fresh.forEach((p) => seen.add(p));
      if (fresh.length === 0) {
        console.error('  codex не сгенерировал PNG — пропуск');
        failed.push(e.slug);
        continue;
      }
      const newest = fresh.map((p) => ({ p, m: statSync(p).mtimeMs })).sort((a, b) => b.m - a.m)[0].p;
      execFileSync('cwebp', ['-resize', '512', '512', '-q', '82', newest, '-o', abs], { stdio: 'inherit' });
      generated.push({ ...e, description, prompt });
      console.log(`  ✓ ${rel}`);
      if (PUSH_EACH) commitAndPush(rel, e.name);
    } catch (err) {
      if (isAuthError(err)) {
        summary(AUTH_FIX);
        process.exit(EXIT_AUTH);
      }
      console.error(`  ошибка на ${e.slug}: ${err?.message || err}`);
      failed.push(e.slug);
    }
  }

  if (PUSH_EACH && generated.length) {
    try { git(['push', 'origin', `HEAD:${GIT_BRANCH}`]); } catch { /* уже залогировано */ }
  }

  summary(`\n### Сгенерировано: ${generated.length}${failed.length ? `, ошибок: ${failed.length}` : ''}`);
  if (generated.length) {
    // Описание — в итог: по нему видно, ЧТО агент понял, ещё до взгляда на картинку.
    summary(generated.map((g) => `- **${g.name}** (\`${g.slug}.webp\`)\n  - _${g.description}_`).join('\n'));
  }
  if (failed.length) summary(`\nПропущены (ретрай в следующем прогоне): ${failed.map((s) => `\`${s}\``).join(', ')}`);

  if (process.env.GITHUB_OUTPUT) {
    appendFileSync(process.env.GITHUB_OUTPUT, `generated_count=${generated.length}\n`);
    appendFileSync(process.env.GITHUB_OUTPUT, `generated_slugs=${generated.map((g) => g.slug).join(',')}\n`);
  }
}

main().catch((err) => {
  summary(`### ❌ Непредвиденная ошибка\n\`\`\`\n${err?.stack || err}\n\`\`\``);
  process.exit(1);
});
