import React from 'react';
import NewsCard from './NewsCard';
import { EnrichedItem } from '../lib/fetchEnriched';

interface HeroProps {
  items: EnrichedItem[];
}

const Hero: React.FC<HeroProps> = ({ items }) => {
  // Ensure we have at least 3 items for hero section
  if (!items || items.length < 3) {
    return (
      <section className="hero" role="region" aria-label="Featured stories">
        <div className="placeholder">
          <p>No featured stories available yet.</p>
        </div>
      </section>
    );
  }

  const [mainStory, ...sideStories] = items.slice(0, 3);

  return (
    <section className="hero" role="region" aria-label="Featured stories">
      {/* Main hero story */}
      <div className="hero-main">
        <NewsCard 
          item={mainStory} 
          isHero={true}
          testId="hero-main-card"
        />
      </div>
      
      {/* Sidebar stories */}
      <div className="hero-sidebar">
        {sideStories.map((item, index) => (
          <NewsCard 
            key={`hero-side-${index}`}
            item={item} 
            isHero={false}
            testId={`hero-side-card-${index}`}
          />
        ))}
      </div>
    </section>
  );
};

export default Hero;
