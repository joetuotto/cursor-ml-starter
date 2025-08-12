import React from 'react';
import { EnrichedItem, formatTimeAgo, clipText } from '../lib/fetchEnriched';

interface NewsCardProps {
  item: EnrichedItem;
  isHero?: boolean;
  testId?: string;
  showLocalFi?: boolean;
  priority?: boolean;
}

const NewsCard: React.FC<NewsCardProps> = ({ item, isHero = false, testId, showLocalFi = false, priority = false }) => {
  const cardClass = isHero ? 'card card-hero' : 'card';
  const ledeMaxLength = isHero ? 300 : 240;
  
  // Use lede_title if available, otherwise fall back to title
  const displayTitle = item.lede_title || item.title;
  
  return (
    <article 
      className={cardClass}
      data-testid={testId || 'news-card'}
    >
      {/* Kicker */}
      <div className="kicker" data-testid="kicker">
        {item.kicker}
      </div>
      
      {/* Headline */}
      <h2 className="headline" data-testid="headline">
        <a 
          href={item.cta.url}
          rel="noopener noreferrer"
          target={item.cta.url.startsWith('http') ? '_blank' : undefined}
        >
          {displayTitle}
        </a>
      </h2>
      
      {/* Lede */}
      <p className="lede" data-testid="lede">
        {showLocalFi && item.local_fi ? 
          clipText(item.local_fi.split('.')[0] + '.', ledeMaxLength) : 
          clipText(item.lede, ledeMaxLength)
        }
      </p>
      
      {/* Finnish perspective section */}
      {showLocalFi && item.local_fi && (
        <div className="finnish-perspective">
          <div className="fi-header">
            <span className="fi-label">🇫🇮 Suomen näkökulma</span>
            {item.local_fi_score && (
              <span className="fi-score">
                {Math.round(item.local_fi_score * 100)}% relevanssi
              </span>
            )}
          </div>
          <div className="fi-content">
            {item.local_fi.split('\n').map((paragraph, i) => (
              paragraph.trim() && <p key={i}>{paragraph.trim()}</p>
            ))}
          </div>
        </div>
      )}
      
      {/* Why it matters (conditional) */}
      {item.why_it_matters && (
        <div className="why" data-testid="why-it-matters">
          <strong>Why it matters:</strong> {item.why_it_matters}
        </div>
      )}
      
      {/* Meta information */}
      <div className="meta">
        <span className="timestamp" data-testid="timestamp">
          {formatTimeAgo(item.published_at)}
        </span>
        
        <a 
          href={item.cta.url}
          className="cta"
          data-testid="cta"
          rel="noopener noreferrer"
          target={item.cta.url.startsWith('http') ? '_blank' : undefined}
          aria-label={`${item.cta.label} for ${displayTitle}`}
        >
          {item.cta.label}
        </a>
      </div>
    </article>
  );
};

export default NewsCard;
