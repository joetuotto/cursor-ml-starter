import React, { useState, useEffect } from 'react';
import NewsCard from '../components/NewsCard';
import { EnrichedItem } from '../lib/fetchEnriched';
import '../styles/ft-newswire.css';

interface FinnishNewsData {
  items: EnrichedItem[];
  total: number;
  origin_country_filter: string;
}

const NewswirePageFi: React.FC = () => {
  const [data, setData] = useState<FinnishNewsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadFinnishData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch Finnish newswire data
        const response = await fetch('/newswire/fi');
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const finnishData: FinnishNewsData = await response.json();
        setData(finnishData);
        
      } catch (err) {
        console.error('Failed to load Finnish news data:', err);
        setError('Suomalaisten uutisten lataus epäonnistui. Yritä myöhemmin uudelleen.');
      } finally {
        setLoading(false);
      }
    };

    loadFinnishData();
  }, []);

  if (loading) {
    return (
      <div className="newswire-page">
        <header className="newswire-header">
          <div className="header-content">
            <div className="header-top">
              <h1 className="header-title">
                <span className="flag-emoji">🇫🇮</span>
                PARANOID Models — Suomi
              </h1>
              <nav className="header-nav">
                <a href="/newswire/#trends" className="nav-link">Global</a>
                <a href="/newswire/fi" className="nav-link active">Suomi</a>
              </nav>
            </div>
            <p className="header-description">
              Suomalaiset talousuutiset ja niiden vaikutukset — syvällisiä analyysejä kotimaisista markkinoista
            </p>
          </div>
        </header>
        
        <main className="newswire-content">
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>Ladataan suomalaisia uutisia...</p>
          </div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="newswire-page">
        <header className="newswire-header">
          <div className="header-content">
            <div className="header-top">
              <h1 className="header-title">
                <span className="flag-emoji">🇫🇮</span>
                PARANOID Models — Suomi
              </h1>
              <nav className="header-nav">
                <a href="/newswire/#trends" className="nav-link">Global</a>
                <a href="/newswire/fi" className="nav-link active">Suomi</a>
              </nav>
            </div>
            <p className="header-description">
              Suomalaiset talousuutiset ja niiden vaikutukset — syvällisiä analyysejä kotimaisista markkinoista
            </p>
          </div>
        </header>
        
        <main className="newswire-content">
          <div className="error-state">
            <h3>Virhe uutisten latauksessa</h3>
            <p>{error}</p>
            <button onClick={() => window.location.reload()} className="retry-button">
              Yritä uudelleen
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="newswire-page">
      <header className="newswire-header">
        <div className="header-content">
          <div className="header-top">
            <h1 className="header-title">
              <span className="flag-emoji">🇫🇮</span>
              PARANOID Models — Suomi
            </h1>
            <nav className="header-nav">
              <a href="/newswire/#trends" className="nav-link">Global</a>
              <a href="/newswire/fi" className="nav-link active">Suomi</a>
            </nav>
          </div>
          <p className="header-description">
            Suomalaiset talousuutiset ja niiden vaikutukset — syvällisiä analyysejä kotimaisista markkinoista
          </p>
          
          {data && (
            <div className="header-stats">
              <span className="stat">
                <strong>{data.total}</strong> uutista
              </span>
              <span className="stat">
                <strong>Finland</strong> focus
              </span>
            </div>
          )}
        </div>
      </header>

      <main className="newswire-content">
        <section className="news-grid">
          {data?.items.map((item, index) => (
            <div key={item.id || index} className="news-card-wrapper">
              <div className="fi-badge">FI</div>
              <NewsCard
                item={item}
                showLocalFi={true}
                priority={index < 3}
              />
            </div>
          ))}
          
          {(!data?.items || data.items.length === 0) && (
            <div className="empty-state">
              <h3>Ei uutisia saatavilla</h3>
              <p>Yritä hetken kuluttua uudelleen.</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
};

export default NewswirePageFi;
