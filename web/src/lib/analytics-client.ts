// Аналитика GA4 через gtag.js (тот же measurementId, что в Firebase Analytics — Firebase Analytics
// это GA4 под капотом). Намеренно НЕ тащим firebase SDK в бандл: грузим лёгкий gtag с Google CDN
// отложенно (не влияет на LCP). Без measurementId — тихо пропускаем.
// Экспортит window.omnisTrack(name, params) для событий (клик CTA-воронки в лист персонажа).
const ID = import.meta.env.VITE_FIREBASE_MEASUREMENT_ID as string | undefined;

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
  function gtag(...args: unknown[]) {
    window.dataLayer!.push(args);
  }
  gtag('js', new Date());
  gtag('config', ID); // авто page_view (трафик)

  window.omnisTrack = (name, params) => gtag('event', name, params);
}
