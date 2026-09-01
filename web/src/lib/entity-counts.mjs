// Сколько сущностей в компендиуме (issue #230). Число берётся из meta.json того же JSON API,
// что кормит сами страницы сущностей, — второго счёта не заводим: иначе хаб документа начнёт
// расходиться с компендиумом в тот день, когда данные обновятся, и никто этого не заметит.
//
// Отсутствие файла — не ошибка: у части узлов NAV (например, «Термины») компендиума нет,
// вызывающий просто не печатает число.
import fs from 'node:fs';
import path from 'node:path';

const API_ROOT = path.resolve(process.cwd(), 'src/data/api');

export function resourceTotal(game, version, lang, resource) {
  if (!resource) return null;
  try {
    const file = path.join(API_ROOT, game, version, lang, resource, 'meta.json');
    const total = JSON.parse(fs.readFileSync(file, 'utf-8')).total;
    return typeof total === 'number' ? total : null;
  } catch {
    return null;
  }
}
