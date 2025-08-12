import { useEffect, useState } from 'react';
import { detectLang, setLang, Lang } from '../lib/i18n';

export default function LanguageToggle() {
  const [lang, setL] = useState<Lang>(detectLang());

  useEffect(() => {
    const h = (e: any) => setL(e.detail);
    window.addEventListener('paranoid:lang', h as any);
    return () => window.removeEventListener('paranoid:lang', h as any);
  }, []);

  return (
    <div className="lang-toggle">
      <button
        className={lang === 'en' ? 'active' : ''}
        onClick={() => { setLang('en'); setL('en'); }}
      >EN</button>
      <span style={{opacity:0.6, margin: '0 6px'}}> / </span>
      <button
        className={lang === 'fi' ? 'active' : ''}
        onClick={() => { setLang('fi'); setL('fi'); }}
      >FI</button>
      <style>{`
        .lang-toggle { display:flex; align-items:center; gap:4px; }
        .lang-toggle button { border:none; background:transparent; cursor:pointer; font-weight:600; }
        .lang-toggle button.active { text-decoration: underline; }
      `}</style>
    </div>
  );
}
