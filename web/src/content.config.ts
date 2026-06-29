import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';

// SRD-контент лежит ВНЕ web/ — в ../src/{game}/{version}/{en,ru}/**.md (вход контентного пайплайна,
// не дублируем). Глоб ограничен реальными играми (dnd|daggerheart|brp) и языками (en|ru), чтобы не
// затянуть translate/-артефакты, dnd-v2 и site/. Frontmatter нет → схема не задаётся.
const srd = defineCollection({
  loader: glob({
    pattern: '@(dnd|daggerheart|brp)/*/@(en|ru)/**/*.md',
    base: '../src',
    // По умолчанию glob слугифицирует id (срезает точку в "srd-5.2" → "srd-52"). Оставляем сырой
    // путь без расширения — slug/URL контролируем сами в lib/slug.ts (parseId/slugifySegment).
    generateId: ({ entry }) => entry.replace(/\.md$/, ''),
  }),
});

export const collections = { srd };
