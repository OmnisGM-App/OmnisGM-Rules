# OmnisGM Rules — rules.omnisgm.com

> Ридер SRD настольных игр (D&D 5.2.1/5.1, Daggerheart 1.0, BRP 1.0) — **продукт экосистемы OmnisGM**.
> Здесь — продукт, стек и инфраструктура. Контентный пайплайн (импорт PDF → markdown → перевод)
> вынесен в **[documentation/content-pipeline.md](documentation/content-pipeline.md)** (#288):
> он живёт своей жизнью и в ежедневной работе над сайтом не нужен.

## Куда смотреть

| Тема | Где |
|---|---|
| Импорт и перевод SRD, скиллы пайплайна, правила `.claude/rules` | [documentation/content-pipeline.md](documentation/content-pipeline.md) |
| Картинки сущностей: формат, раскладка, промты | [documentation/entity-images.md](documentation/entity-images.md), [image-prompts.md](documentation/image-prompts.md) |
| Продукт, стек, инфраструктура, накопленные грабли | этот файл ниже |

## Продукт и экосистема OmnisGM

### Расстановка продуктов
- **Основной** — интерактивный лист персонажа.
- **Доп** — новости (The Guild Herald, news.omnisgm.com; отдельное репо `OmnisGM-News`).
- **Этот** — правила/SRD (`rules.omnisgm.com`).

### Главная цель — SEO-воронка в основной продукт
Человек гуглит уточнение по правилу → попадает на нашу **статичную** страницу правил → CTA уводит его
в интерактивный лист персонажа. Поэтому **SEO критичен** и контент **обязан рендериться в статический HTML**
(НЕ client-rendered SPA — именно client-render убил SEO новостям: краулер видит пустой `<div id=root>`).

### Стек публикации — Astro (SSG)
Публикует сайт **Astro (SSG)**; прежний MkDocs Material + GitHub Pages выведен из эксплуатации
(`pages.yml` удалён). Контентный пайплайн импорта/перевода от движка не зависит — он производит
`.md`, которые потребляет сайт.

Почему Astro: (1) дизайнер отдал готовые **React-компоненты**, и Astro умеет и принять их
островами, и отдать статикой; (2) **PWA обязателен** (first-class `@vite-pwa/astro`);
(3) общий стек с экосистемой. По факту сборки островов не понадобилось: компоненты перенесены
как `.astro`, и страницы уезжают zero-JS — SEO целы по построению.

Остатки MkDocs снесены (#296): каталог src/site, скрипты prepare_docs.sh и
split_sitemap.py, записи `/site/ /docs/ /mkdocs.yml /overrides/` в `.gitignore`. (Пути здесь
без бэктиков намеренно: гейт ссылок читает их как заявление о живом инструменте, а этих
файлов больше нет.) Скилл `/integrate-srd` при этом ЖИВ: он переписан под Astro (#318) и
MkDocs-файлов больше не трогает — он и есть чеклист интеграции, а
`documentation/content-pipeline.md` только ведёт к нему.

Что мёртвый инструментарий не отрастёт снова, держит гейт `scripts/test_doc_links.mjs`: путь
к скрипту, скиллу, правилу или workflow, названный в документации или в скилле, обязан
существовать. Ссылка внутри ```-блока проверяется наравне с инлайновой — именно так скилл
называет свои хелперы.

- **Раскладка:** Astro-приложение в отдельной папке **`web/`**. `src/` репо — это Markdown-контент
  (`src/{game}/{version}/{en,ru}/*.md`), вход контентного пайплайна — **не трогать**. Content collections
  Astro ссылаются на `src/{game}/...md`. Динамические роуты `/{lang}/{game}/{version}/{...slug}` через
  `getStaticPaths` (статика). Markdown рендерится **на билде**, не в браузере.
- **Интеграции:** `@vite-pwa/astro` (PWA — обязателен), **Pagefind** (статический поиск),
  `@astrojs/sitemap`. i18n EN/RU + hreflang, sitemap, JSON-LD. React в стеке НЕТ: компоненты
  дизайнера перенесены как `.astro`, островов в проекте ни одного (ревью #297) — если он
  понадобится, это отдельное решение, а не «уже подключено».
- **SEO-воронка:** CTA-блок «в лист персонажа» на каждой странице; событие Analytics на клик CTA.

### Дизайн
claude.ai/design проект `28349954-9a6f-47fd-a34d-406e6775544e` (тот же, где Gazette новостей).
Читается через DesignSync (`get_file`). Файлы: `Rules.html` (обёртка-превью вьюпортов),
**`rules-docs.jsx` — компонент `RulesDocsApp`, реальный UI**; `rules-docs.css`; `rules-docs-data.jsx`;
общий `omnis-site.css` + `site-shell.jsx` (`OmnisSeal`, токены `C`). Скин ридера: топбар (печать OmnisGM +
«OmnisGM / rules», поиск-типахед, GitHub, ENG/RU, бургер) → вкладки систем → слева nav-дерево, центр
Markdown, справа TOC «На этой странице» → prev/next, строка «Источник», мобильный drawer.

### Инфраструктура
- **Репо:** `OmnisGM-App/OmnisGM-Rules`. Локально склонирован `/Users/petrradilov/Documents/OmnisGM/OmnisGM-Rules`
  рядом с `OmnisGM News`.
- **Firebase:** ОТДЕЛЬНЫЙ проект **`omnisgm-rules`** (не `omnisgm-news`). Hosting + домен `rules.omnisgm.com`
  (DNS владелец настроит после поднятия хостинга).
- **Секреты/переменные репо:** `FIREBASE_SERVICE_ACCOUNT` (secret, SA-ключ деплоя — ставить `gh secret set < файл`
  НЕ читая). Клиентский `firebaseConfig` — 7 публичных значений в **repo variables** `VITE_FIREBASE_*`
  (variables, НЕ secrets — web apiKey не credential).
- **Analytics:** `measurementId G-RRH57ELLZS` — трафик + конверсия CTA-воронки; отдельный
  client-island, на статический HTML / SEO не влияет.
- **Деплой:** `astro build` + `firebase deploy --only hosting` (проект `omnisgm-rules`).
  JSON API собирает `hosting.predeploy` в `firebase.json` (`generate_api.py` по разу на игру),
  релизы — `.github/workflows/release.yml` (rolling-тег `latest`).

### Инфраструктурные нарративы — в `.claude/rules/` (paths-скоуп)

Глубокие «почему»-разделы вынесены в правила; подключаются автоматически при работе
с соответствующими файлами:

- `e2e-ports-guard.md` — слот портов `OMNISGM_SLOT` + страж свежести сборки (Table#469, #251)
- `seo-dates-hubs.md` — даты JSON-LD из git, lastmod в sitemap, хабы документов, крошки,
  эмулятор ≠ прод по редиректам (#219, #221, #230, #220)
- `security-headers-csp.md` — заголовки в `firebase.json`, CSP enforce и как её проверять (#218, #225)
- `cloudflare-cache.md` — правка заголовков требует сброса зоны; проверки после релиза — по origin (#227)
- `codex-images.md` — картинки сущностей, CLS-тест, ранбук токена codex (#201, #202)

### Связка setup в workflow — один общий шаг (#287)
`setup-node` + кэш + `npm ci` + `setup-python` живут в composite-действии
`.github/actions/setup-web`; workflow зовут `- uses: ./.github/actions/setup-web`. Версии Node
и Python объявлены ТОЛЬКО там (дефолты входов), а отказ от них пишется явно — `node-version: ''`
у джобы на одном Python. Держит `scripts/test_workflow_setup.mjs`:
он запрещает прямые `actions/setup-node`/`setup-python` в наших workflow и в composite-действиях,
запрещает свои литералы версий у вызывающих и требует `timeout-minutes` у каждой джобы (без него
зависший шаг держит очередь до дефолтных шести часов — `release` однажды упёрся в 360 минут).
Исключение одно: вендорный `claude-review.yml`.

### Наблюдатель за продом (#284)
`.github/workflows/health.yml` — ежедневный крон (06:00 UTC) + ручной запуск. Гоняет уже
написанные проверки, у которых до этого не было вызывающего: edge-кэш Cloudflare, security-заголовки
(дважды — через боевой домен и по origin `omnisgm-rules.web.app`, см. ловушку #227 выше) и нарушения
CSP браузером. Curl-проверки идут ПЕРВЫМИ, до установки Node и Chromium: блип инфраструктуры не
должен утопить проверки, которым она не нужна. Красная джоба = письмо GitHub владельцу.

### Локальные гейты и pre-commit
`npm run test:unit` (node-юниты), `npm run test:unit:py` (python-гейты), `npm run test:gates` —
всё сразу; состав сверяется с `ci.yml` стражем `scripts/test_unit_agenda.mjs`.

Хук подключается корневым **`npm install`** — именно в корне, без `--prefix web`: `npm ci
--prefix web` корневой `prepare` не выполняет, и хука не будет. Уже настроенный
`core.hooksPath` скрипт установки не трогает, а называет. Обойти хук — `SKIP_HOOK=1` или
`git commit --no-verify`.

### Стиль работы владельца
Инкрементально, ревьюит каждый шаг; деплой/пуш — по явной просьбе; **«аудит ≠ фиксы»** (на «проверь/убедись»
сначала репорт, код не менять, пока не скажет «делай»); предпочитает обобщённые модели данных.
