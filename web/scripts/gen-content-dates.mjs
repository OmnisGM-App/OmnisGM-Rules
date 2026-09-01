// Даты изменения контента для JSON-LD (issue #219) — и, дальше, для lastmod в sitemap (#221).
//
// Astro при сборке знает только «сейчас», поэтому datePublished/dateModified неоткуда взять
// иначе как из истории git: дата коммита, тронувшего исходный markdown. Мы НЕ берём mtime
// файла — в CI это время checkout'а, то есть у всех страниц разом дата билда; ровно эту
// ловушку и просили обойти.
//
// Один проход `git log --name-only` по src/ строит карту: путь .md → { published, modified }.
// Лог идёт от новых к старым, поэтому первая встреча файла — последнее изменение, последняя —
// появление. Переименования не отслеживаем (`--follow` пришлось бы звать на каждый файл):
// у переименованного файла published станет датой переименования — редкий случай, а цена
// точности здесь несоразмерна.
//
// НА МЕЛКОМ КЛОНЕ (fetch-depth: 1) истории нет, и честного ответа тоже: тогда пишем пустую
// карту с пометкой shallow, а страницы просто не получают дат. Пустая дата лучше, чем
// одинаковая дата билда на 6000 страниц — Google такую «свежесть» считает шумом.
//
// Запуск: node web/scripts/gen-content-dates.mjs (в prebuild, до astro build).
import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '../..');
const outFile = resolve(here, '../src/data/content-dates.json');

const git = (...args) =>
  execFileSync('git', args, { cwd: repoRoot, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });

let shallow = false;
let files = {};

try {
  shallow = git('rev-parse', '--is-shallow-repository').trim() === 'true';
  if (shallow) {
    console.warn(
      '[gen-content-dates] мелкий клон (fetch-depth: 1) — истории нет, даты не проставляем.\n' +
        '  Для полных дат в CI нужен actions/checkout с fetch-depth: 0 (и filter: blob:none, чтобы не тащить блобы).',
    );
  } else {
    // %x00 — разделитель записей, дальше ISO-дата коммита и его файлы.
    const log = git('log', '--format=%x00%aI', '--name-only', '--', 'src');
    for (const block of log.split('\0')) {
      const lines = block.split('\n').filter(Boolean);
      if (!lines.length) continue;
      const date = lines[0];
      for (const file of lines.slice(1)) {
        if (!file.endsWith('.md') || !file.startsWith('src/')) continue;
        const key = file.slice('src/'.length);
        const rec = files[key];
        // Лог идёт от новых к старым: первая встреча — modified, каждая следующая — published.
        if (rec) rec.published = date;
        else files[key] = { published: date, modified: date };
      }
    }
  }
} catch (err) {
  // Сборка без git (архив исходников, чужая песочница) — не повод валить билд.
  console.warn(`[gen-content-dates] git недоступен (${err.message.split('\n')[0]}) — даты не проставляем.`);
  files = {};
  shallow = true;
}

mkdirSync(dirname(outFile), { recursive: true });
writeFileSync(outFile, JSON.stringify({ shallow, files }, null, 0));
console.log(
  shallow
    ? `[gen-content-dates] дат нет (shallow) → ${outFile}`
    : `[gen-content-dates] ${Object.keys(files).length} файлов → ${outFile}`,
);
