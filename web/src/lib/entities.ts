// Загрузка структурированных сущностей (заклинания/состояния/…) для programmatic-страниц.
// Данные готовит prebuild-скрипт (scripts/gen-entity-data.mjs) в src/data/api/ — тот же
// парсер, что и публичный /api. Читаем с диска в getStaticPaths (Node на этапе билда).
import fs from 'node:fs';
import path from 'node:path';

// Билд запускается из web/ (cwd) — резолвим от него, а не от import.meta.url
// (в бандле Astro последний указывает в dist/ и ломает относительный путь).
const DATA_ROOT = path.resolve(process.cwd(), 'src/data/api');

// Ключ версии в API → сегмент версии в URL (как в читалке).
export const VERSION_SLUG: Record<string, string> = {
  srd52: 'srd-5.2',
  srd51: 'srd-5.1',
};

// Короткая метка версии для заголовков/сниппетов.
export const VERSION_LABEL: Record<string, string> = {
  srd52: '5.2',
  srd51: '5.1',
};

export interface Entity {
  slug: string;
  name: string;
  name_en?: string | null;
  description_md?: string;
  [key: string]: unknown;
}

export function loadEntities(ver: string, lang: string, resource: string): Entity[] {
  const file = path.join(DATA_ROOT, 'dnd', ver, lang, resource, 'all.json');
  if (!fs.existsSync(file)) return [];
  return JSON.parse(fs.readFileSync(file, 'utf-8')) as Entity[];
}

// Плоский текстовый сниппет из markdown (для <meta description>): снимаем разметку,
// схлопываем пробелы, режем по границе слова до ~limit символов.
export function excerpt(md: string | undefined, limit = 155): string {
  if (!md) return '';
  const plain = md
    .replace(/\*\*_?([^*]+?)_?\*\*/g, '$1') // bold / bold-italic
    .replace(/[*_`>#]/g, '')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1') // ссылки → текст
    .replace(/\s+/g, ' ')
    .trim();
  if (plain.length <= limit) return plain;
  const cut = plain.slice(0, limit);
  const lastSpace = cut.lastIndexOf(' ');
  return `${cut.slice(0, lastSpace > 0 ? lastSpace : limit).trim()}…`;
}
