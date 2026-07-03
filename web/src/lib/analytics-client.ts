// Аналитика GA4 через gtag.js (тот же measurementId, что в Firebase Analytics — Firebase Analytics
// это GA4 под капотом). Намеренно НЕ тащим firebase SDK в бандл: грузим лёгкий gtag с Google CDN
// отложенно (не влияет на LCP). Без measurementId — тихо пропускаем.
// Экспортит window.omnisTrack(name, params) для событий (клик CTA-воронки в лист персонажа).
// Префикс PUBLIC_, а не VITE_: Astro отдаёт клиентским скриптам только PUBLIC_-переменные
// (переопределяет vite'овский envPrefix). С VITE_ значение на клиенте — undefined, и минификатор
// вырезал весь gtag-блок из бандла (GA4 не работал на проде вообще). См. #18.
const ID = import.meta.env.PUBLIC_FIREBASE_MEASUREMENT_ID as string | undefined;

declare global {
  interface Window {
    dataLayer?: unknown[];
    omnisTrack?: (name: string, params?: Record<string, unknown>) => void;
  }
}

export function initAnalytics(): void {
  if (!ID || typeof document === 'undefined') return;

  const s = document.createElement('script');
  s.async = true;
  s.src = `https://www.googletagmanager.com/gtag/js?id=${ID}`;
  document.head.appendChild(s);

  window.dataLayer = window.dataLayer || [];
  // gtag.js принимает ТОЛЬКО объект arguments — массив от rest-параметров он молча
  // игнорирует (команды не применяются, хиты не шлются). Поэтому push(arguments),
  // функция обязана быть не-стрелочной. Проверено вживую в #18.
  function gtag(..._args: unknown[]) {
    // eslint-disable-next-line prefer-rest-params
    window.dataLayer!.push(arguments);
  }
  gtag('js', new Date());
  gtag('config', ID); // авто page_view (трафик)

  window.omnisTrack = (name, params) => gtag('event', name, params);
}
