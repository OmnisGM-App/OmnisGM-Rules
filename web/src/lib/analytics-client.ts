// Клиентская инициализация Firebase Analytics (GA4). Грузится отложенным module-скриптом из
// Reader.astro, чтобы не влиять на LCP. Если конфига нет (VITE_FIREBASE_* не заданы) — тихо пропускаем.
// Экспортит window.omnisTrack(name, params) для событий (например, клик CTA-воронки в лист персонажа).
import { initializeApp } from 'firebase/app';
import { getAnalytics, isSupported, logEvent } from 'firebase/analytics';

const cfg = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID,
};

declare global {
  interface Window {
    omnisTrack?: (name: string, params?: Record<string, unknown>) => void;
  }
}

export async function initAnalytics(): Promise<void> {
  if (!cfg.apiKey || !cfg.measurementId) return; // нет конфига — не инициализируем
  try {
    if (!(await isSupported())) return;
    const app = initializeApp(cfg);
    const analytics = getAnalytics(app); // авто-событие page_view (трафик)
    window.omnisTrack = (name, params) => {
      try {
        logEvent(analytics, name, params);
      } catch {
        /* no-op */
      }
    };
  } catch {
    /* analytics не критичен — игнорируем сбои */
  }
}
