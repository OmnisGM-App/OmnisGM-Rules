// Ссылка подкласса на странице заклинания (#367): подпись из `spells.subclasses` → класс и якорь.
import { subclassLinker } from '../src/lib/spell-subclass-links.mjs';

let failed = 0;
const eq = (/** @type {unknown} */ actual, /** @type {unknown} */ expected, /** @type {string} */ what) => {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    failed++;
    console.error(`  ✗ ${what}\n      ожидалось ${JSON.stringify(expected)}, получено ${JSON.stringify(actual)}`);
  }
};

const data = {
  en: {
    subclasses: [
      { slug: 'circle-of-the-land', name: 'Circle of the Land', class: 'druid' },
      { slug: 'fiend-patron', name: 'Fiend Patron', class: 'warlock' },
      { slug: 'life-domain', name: 'Life Domain', class: 'cleric' },
      { slug: 'oath-of-devotion', name: 'Oath of Devotion', class: 'paladin' },
      { slug: 'draconic-sorcery', name: 'Draconic Sorcery', class: 'sorcerer' },
      { slug: 'hunter', name: 'Hunter', class: 'ranger' },
    ],
    classes: [
      { slug: 'druid', name: 'Druid' }, { slug: 'warlock', name: 'Warlock' }, { slug: 'cleric', name: 'Cleric' },
      { slug: 'paladin', name: 'Paladin' }, { slug: 'sorcerer', name: 'Sorcerer' }, { slug: 'ranger', name: 'Ranger' },
    ],
  },
  ru: {
    subclasses: [
      { slug: 'circle-of-the-land', name: 'Круг Земли', class: 'druid' },
      { slug: 'fiend-patron', name: 'Покровитель: Исчадие', class: 'warlock' },
      { slug: 'life-domain', name: 'Домен жизни', class: 'cleric' },
      { slug: 'oath-of-devotion', name: 'Клятва преданности', class: 'paladin' },
      { slug: 'draconic-sorcery', name: 'Драконье чародейство', class: 'sorcerer' },
      { slug: 'hunter', name: 'Охотник', class: 'ranger' },
    ],
    classes: [
      { slug: 'druid', name: 'Друид' }, { slug: 'warlock', name: 'Колдун' }, { slug: 'cleric', name: 'Жрец' },
      { slug: 'paladin', name: 'Паладин' }, { slug: 'sorcerer', name: 'Чародей' }, { slug: 'ranger', name: 'Следопыт' },
    ],
  },
};
const linker = (/** @type {'en' | 'ru'} */ lang) =>
  subclassLinker(data[lang].subclasses, data[lang].classes, { lang, classUrl: (slug) => `/${lang}/dnd/srd-5.2/classes/${slug}/` });

const en = linker('en');
eq(en('Circle of the Land (Arid Land)'), { className: 'Druid', href: '/en/dnd/srd-5.2/classes/druid/#druid-subclass-circle-of-the-land' },
  'EN: подпись с выбором находит подкласс по имени до скобок');
eq(en('Fiend Patron'), { className: 'Warlock', href: '/en/dnd/srd-5.2/classes/warlock/#warlock-subclass-fiend-patron' }, 'EN: колдун');
eq(en('Life Domain'), { className: 'Cleric', href: '/en/dnd/srd-5.2/classes/cleric/#cleric-subclass-life-domain' }, 'EN: жрец');
eq(en('Oath of Devotion'), { className: 'Paladin', href: '/en/dnd/srd-5.2/classes/paladin/#paladin-subclass-oath-of-devotion' }, 'EN: паладин');
eq(en('Draconic Sorcery'), { className: 'Sorcerer', href: '/en/dnd/srd-5.2/classes/sorcerer/#sorcerer-subclass-draconic-sorcery' }, 'EN: чародей');
eq(en('Hunter'), { className: 'Ranger', href: '/en/dnd/srd-5.2/classes/ranger/' }, 'подкласс без якоря — ссылка на страницу класса');
eq(en('Fiend'), null, 'подпись не из ресурса — без ссылки');
eq(en('Hunter Gatherer'), null, 'имя подкласса как начало другой подписи — не совпадение');

const ru = linker('ru');
eq(ru('Круг Земли (Засушливая земля)'), { className: 'Друид', href: '/ru/dnd/srd-5.2/classes/druid/#подкласс-друида-круг-земли' }, 'RU: друид с типом земли');
eq(ru('Покровитель: Исчадие'), { className: 'Колдун', href: '/ru/dnd/srd-5.2/classes/warlock/#подкласс-колдуна-покровитель-исчадие' }, 'RU: колдун');
eq(ru('Домен жизни'), { className: 'Жрец', href: '/ru/dnd/srd-5.2/classes/cleric/#подкласс-жреца-домен-жизни' }, 'RU: жрец');
eq(ru('Клятва преданности'), { className: 'Паладин', href: '/ru/dnd/srd-5.2/classes/paladin/#подкласс-паладина-клятва-преданности' }, 'RU: паладин');
eq(ru('Драконье чародейство'), { className: 'Чародей', href: '/ru/dnd/srd-5.2/classes/sorcerer/#подкласс-чародея-драконье-чародейство' }, 'RU: чародей');

if (failed) {
  console.error(`❌ spell-subclass-links: ${failed}`);
  process.exit(1);
}
console.log('✅ spell-subclass-links: подпись подкласса → класс и якорь, EN и RU');
