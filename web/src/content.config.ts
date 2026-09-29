import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';

// SRD-контент лежит ВНЕ web/ (вход контентного пайплайна). Frontmatter нет → схема не задаётся.
const srd = defineCollection({
  loader: glob({
    pattern: '@(dnd|daggerheart|brp)/*/@(en|ru)/**/*.md',
    base: '../src',
    // Сырой путь: glob по умолчанию срезает точку в "srd-5.2"; URL строит lib/slug.ts.
    generateId: ({ entry }) => entry.replace(/\.md$/, ''),
  }),
});

export const collections = { srd };
