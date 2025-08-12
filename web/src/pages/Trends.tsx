import { useEffect, useState } from 'react';
import { detectLang, Lang } from '../lib/i18n';

type Card = {
  kicker: string; headline: string; lede: string;
  analysis: string; risk_scenario: string; why_it_matters: string;
  sources: string[]; lang: 'en'|'fi';
  id?: string;
  image?: {
    hero: string;
    card: string;
    thumb: string;
    attribution?: {
      author: string;
      source_url: string;
      license: string;
      license_url: string;
    };
  };
  og_image?: string;
};

export default function Trends() {
  const [lang, setLang] = useState<Lang>(detectLang());
  const [cards, setCards] = useState<Card[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const onChange = (e: any) => setLang(e.detail);
    window.addEventListener('paranoid:lang', onChange as any);
    return () => window.removeEventListener('paranoid:lang', onChange as any);
  }, []);

  useEffect(() => {
    const path = window.location.pathname.toLowerCase();
    if (path.includes('/fi/')) window.dispatchEvent(new CustomEvent('paranoid:lang', { detail: 'fi' }));
    if (path.includes('/en/')) window.dispatchEvent(new CustomEvent('paranoid:lang', { detail: 'en' }));
  }, []);

  useEffect(() => {
    setLoading(true);
    // Try local first, fallback to GCS
    const localFeed = lang === 'fi' ? '/newswire/trends.fi.json' : '/newswire/trends.en.json';
    const gcsFeed = lang === 'fi' 
      ? 'https://storage.googleapis.com/paranoidmodels.com/newswire/trends.fi.json'
      : 'https://storage.googleapis.com/paranoidmodels.com/newswire/trends.en.json';
    
    fetch(localFeed, { cache: 'no-store' })
      .then(r => {
        if (!r.ok) throw new Error('Local feed not found');
        return r.json();
      })
      .catch(() => {
        console.log('Falling back to GCS feed:', gcsFeed);
        return fetch(gcsFeed, { cache: 'no-store' }).then(r => r.json());
      })
      .then(setCards)
      .finally(() => setLoading(false));
  }, [lang]);

  if (loading) return <div>Loading…</div>;

  return (
    <div className="trends">
      {cards.map((c, i) => (
        <article key={i} className="card">
          {c.image && (
            <div className="card-image">
              <img 
                src={c.image.card} 
                alt={c.headline}
                loading="lazy"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
              />
            </div>
          )}
          <div className="card-content">
            <div className="kicker">{c.kicker}</div>
            <h3 className="headline">{c.headline}</h3>
            <p className="lede">{c.lede}</p>
            <p className="analysis">{c.analysis}</p>
            <p className="risk"><strong>{lang==='fi'?'Riskiskenaario':'Risk scenario'}:</strong> {c.risk_scenario}</p>
            <p className="wim"><strong>{lang==='fi'?'Miksi tämä on olennaista':'Why it matters'}:</strong> {c.why_it_matters}</p>
            <ul className="sources">
              {(c.sources||[]).map((s,idx)=><li key={idx}><a href={s} target="_blank" rel="noreferrer">{s}</a></li>)}
            </ul>
            {c.image?.attribution && (
              <p className="image-credit">
                Image: <a href={c.image.attribution.source_url} target="_blank" rel="noreferrer">{c.image.attribution.author}</a> / 
                <a href={c.image.attribution.license_url} target="_blank" rel="noreferrer">{c.image.attribution.license}</a>
              </p>
            )}
          </div>
        </article>
      ))}
      <style>{`
        .trends { max-width: 1200px; margin: 0 auto; }
        .card { 
          padding: 20px; 
          border-bottom: 1px solid #222; 
          display: flex;
          gap: 20px;
          transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .card:hover {
          transform: scale(1.01);
          box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        .card-image {
          flex-shrink: 0;
          width: 300px;
          height: 168px;
          border-radius: 12px;
          overflow: hidden;
        }
        .card-image img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          transition: transform 0.2s ease;
        }
        .card:hover .card-image img {
          transform: scale(1.02);
        }
        .card-content {
          flex: 1;
        }
        .kicker { 
          font-size: 12px; 
          opacity: .7; 
          letter-spacing: .08em; 
          text-transform: uppercase;
          color: #59D3A2;
          margin-bottom: 8px;
        }
        .headline { 
          font-weight: 700; 
          margin: 0 0 12px 0;
          font-size: 24px;
          line-height: 1.3;
        }
        .lede { 
          opacity: .9; 
          margin-bottom: 16px;
          font-size: 16px;
          line-height: 1.5;
        }
        .analysis { 
          margin-top: 12px;
          line-height: 1.6;
        }
        .risk, .wim { 
          margin-top: 12px;
          line-height: 1.6;
        }
        .sources { 
          margin-top: 16px; 
          opacity: .9;
          font-size: 14px;
        }
        .sources a {
          color: #59D3A2;
          text-decoration: none;
        }
        .sources a:hover {
          text-decoration: underline;
        }
        .image-credit {
          margin-top: 12px;
          font-size: 11px;
          opacity: 0.6;
          color: #888;
        }
        .image-credit a {
          color: #59D3A2;
          text-decoration: none;
        }
        .image-credit a:hover {
          text-decoration: underline;
        }
        @media (max-width: 768px) {
          .card {
            flex-direction: column;
            padding: 16px;
          }
          .card-image {
            width: 100%;
            height: 200px;
          }
          .headline {
            font-size: 20px;
          }
        }
      `}</style>
    </div>
  );
}
