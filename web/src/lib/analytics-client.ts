// Аналитика: GA4 (gtag.js) + Яндекс.Метрика. Оба грузятся отложенно с CDN (не тащим
// SDK в бандл, не влияем на LCP). Каждый gated на свой ID — без ID тихо пропускаем.
// Экспортит window.omnisTrack(name, params): одна CTA-точка шлёт событие в GA4 И
// reachGoal в Метрику (воронка Rules→лист персонажа видна в обеих системах).
// Префикс PUBLIC_, а не VITE_: Astro отдаёт клиентским скриптам только PUBLIC_-переменные
// (иначе значение на клиенте undefined и минификатор вырезает блок). См. #18 (GA4), #27 (Метрика).
const GA_ID = import.meta.env.PUBLIC_FIREBASE_MEASUREMENT_ID as string | undefined;
const YM_ID = import.meta.env.PUBLIC_METRIKA_ID as string | undefined;

type YmFn = { (...args: unknown[]): void; a?: unknown[]; l?: number };

declare global {
  interface Window {
    dataLayer?: unknown[];
    ym?: YmFn;
    omnisTrack?: (name: string, params?: Record<string, unknown>) => void;
  }
}

// GA4 через gtag.js. Возвращает gtag-функцию для событий (или undefined без ID).
function initGA4(id: string): ((...args: unknown[]) => void) | undefined {
  const s = document.createElement('script');
  s.async = true;
  s.src = `https://www.googletagmanager.com/gtag/js?id=${id}`;
  document.head.appendChild(s);

  window.dataLayer = window.dataLayer || [];
  // gtag.js принимает ТОЛЬКО объект arguments — массив от rest-параметров он молча
  // игнорирует. Поэтому push(arguments), функция обязана быть не-стрелочной. См. #18.
  function gtag(..._args: unknown[]) {
    // eslint-disable-next-line prefer-rest-params
    window.dataLayer!.push(arguments);
  }
  gtag('js', new Date());
  gtag('config', id); // авто page_view (трафик)
  return gtag;
}

// Яндекс.Метрика (tag.js). Вебвизор ВКЛ — контент Rules публичный (#27).
function initMetrika(id: number): void {
  // Официальный сниппет Метрики кладёт в очередь ОБЪЕКТ arguments (tag.js читает её
  // индексным доступом) — не массив. Не-стрелочная функция + push(arguments), как у gtag
  // (шрам #18): формат очереди побайтово совпадает с эталоном.
  window.ym =
    window.ym ||
    function () {
      // eslint-disable-next-line prefer-rest-params
      (window.ym!.a = window.ym!.a || []).push(arguments);
    };
  window.ym.l = 1 * (new Date() as unknown as number);
  const s = document.createElement('script');
  s.async = true;
  s.src = 'https://mc.yandex.ru/metrika/tag.js';
  document.head.appendChild(s);
  window.ym(id, 'init', {
    clickmap: true,
    trackLinks: true,
    accurateTrackBounce: true,
    webvisor: true,
  });
}

export function initAnalytics(): void {
  if (typeof document === 'undefined') return;

  const gtag = GA_ID ? initGA4(GA_ID) : undefined;
  const ymId = YM_ID ? Number(YM_ID) : NaN;
  const hasYm = Number.isFinite(ymId);
  if (hasYm) initMetrika(ymId);

  if (!gtag && !hasYm) return;

  window.omnisTrack = (name, params) => {
    gtag?.('event', name, params);
    if (hasYm) window.ym?.(ymId, 'reachGoal', name, params);
  };
}
