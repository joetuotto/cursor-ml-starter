import React, { useState, useEffect } from 'react';
import Hero from '../components/Hero';
import NewsCard from '../components/NewsCard';
import { EnrichedData, EnrichedItem, fetchEnrichedData, sortByPublishedDate } from '../lib/fetchEnriched';
import '../styles/ft-newswire.css';

const NewswirePage: React.FC = () => {
  const [data, setData] = useState<EnrichedData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const enrichedData = await fetchEnrichedData();
        
        // Sort items by published date (newest first)
        const sortedItems = sortByPublishedDate(enrichedData.items);
        
        setData({
          ...enrichedData,
          items: sortedItems
        });
      } catch (err) {
        console.error('Failed to load enriched data:', err);
        setError('Failed to load news data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  if (loading) {
    return (
      <div className="page">
        <div className="loading" role="status" aria-live="polite">
          <span className="visually-hidden">Loading news content...</span>
          Loading latest analysis...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page">
        <div className="error" role="alert">
          <strong>Error:</strong> {error}
        </div>
      </div>
    );
  }

  if (!data || !data.items || data.items.length === 0) {
    return (
      <div className="page">
        <div className="placeholder">
          <h2>No enriched items yet</h2>
          <p>The newswire is being prepared. Please check back soon for the latest analysis and insights.</p>
        </div>
      </div>
    );
  }

  // Split items: first 3 for hero, rest for grid
  const heroItems = data.items.slice(0, 3);
  const gridItems = data.items.slice(3);

  return (
    <div className="page">
      {/* Navigation */}
      <header className="nav" role="banner">
        <a href="/" className="brand">
          Paranoid Models
        </a>
        <nav role="navigation">
          <ul className="nav-links">
            <li><a href="/newswire/#trends">Trends</a></li>
            <li><a href="#analysis">Analysis</a></li>
            <li><a href="#insights">Insights</a></li>
          </ul>
        </nav>
      </header>

      {/* Main content */}
      <main role="main">
        {/* Hero section */}
        <Hero items={heroItems} />

        {/* Grid section */}
        {gridItems.length > 0 && (
          <>
            <div className="section-title" role="heading" aria-level={2}>
              Latest Analysis
            </div>
            <section 
              className="grid" 
              role="region" 
              aria-label="Latest analysis articles"
            >
              {gridItems.map((item, index) => (
                <NewsCard 
                  key={`grid-${index}-${item.published_at}`}
                  item={item}
                  testId={`grid-card-${index}`}
                />
              ))}
            </section>
          </>
        )}

        {/* Summary section (if available) */}
        {data.summary && (
          <section 
            className="summary" 
            role="region" 
            aria-label="Executive summary"
            style={{
              background: '#fff',
              border: '1px solid var(--line)',
              borderRadius: 'var(--r)',
              padding: '20px',
              marginTop: '32px',
              fontStyle: 'italic',
              color: 'var(--ink2)'
            }}
          >
            <h3 style={{ 
              margin: '0 0 12px 0', 
              fontFamily: 'var(--font-serif)',
              color: 'var(--ink)',
              fontSize: '18px'
            }}>
              Executive Summary
            </h3>
            <p style={{ margin: 0, lineHeight: 1.6 }}>
              {data.summary}
            </p>
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="footer" role="contentinfo">
        <p>
          Analysis generated at {new Date(data.generated_at).toLocaleString()} • 
          <a href="#methodology" style={{ marginLeft: '8px', color: 'var(--plum)' }}>
            Methodology
          </a> • 
          <a href="#about" style={{ marginLeft: '8px', color: 'var(--plum)' }}>
            About
          </a>
        </p>
      </footer>
    </div>
  );
};

export default NewswirePage;
