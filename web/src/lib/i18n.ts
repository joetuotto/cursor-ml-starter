// web/src/lib/i18n.ts
export type Lang = 'en' | 'fi';

export function detectLang(): Lang {
  const stored = localStorage.getItem('paranoid_lang') as Lang | null;
  if (stored) return stored;
  const nav = navigator.language.toLowerCase();
  return nav.startsWith('fi') ? 'fi' : 'en';
}

export function setLang(l: Lang) {
  localStorage.setItem('paranoid_lang', l);
  window.dispatchEvent(new CustomEvent('paranoid:lang', { detail: l }));
}
