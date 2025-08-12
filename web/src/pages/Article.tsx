import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { useLanguage } from "../utils/lang";
import { fetchFeed, type Card } from "../data/fetchFeed";
import { heroFor } from "../utils/hero";

export default function Article() {
  const { id } = useParams();
  const { lang } = useLanguage();
  const [item, setItem] = useState<Card | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFeed(lang).then((arr) => {
      setItem(arr.find(x => x.id === id) || null);
      setLoading(false);
    });
  }, [id, lang]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-fog/70">Loading report...</div>
      </div>
    );
  }

  if (!item) {
    return (
      <div className="text-center py-16">
        <h1 className="font-serif text-2xl text-fog/70">Report Not Found</h1>
        <p className="text-fog/50 mt-2">The requested intelligence report could not be located.</p>
      </div>
    );
  }

  const heroUrl = item.image?.hero || heroFor(item.category);

  return (
    <article className="max-w-4xl mx-auto">
      <header className="mb-8">
        <p className="uppercase text-[11px] tracking-widest text-gild mb-4">{item.kicker}</p>
        <h1 className="font-serif text-4xl leading-tight mb-6">{item.headline}</h1>
        
        {heroUrl && (
          <div className="relative rounded-xl overflow-hidden mb-6 h-64">
            <img 
              src={heroUrl} 
              className="w-full h-full object-cover"
              style={{ filter: "grayscale(100%) contrast(1.15) brightness(0.88)" }}
              alt="" 
            />
            <div className="absolute inset-0 bg-gradient-to-t from-ink/60 via-transparent to-transparent" />
            
            {item.image?.attribution && (
              <div className="absolute bottom-2 right-3 text-[10px] text-bone/70">
                <a href={item.image.attribution.source_url} target="_blank" rel="noopener noreferrer" className="hover:text-bone">
                  {item.image.attribution.author}
                </a> / 
                <a href={item.image.attribution.license_url} target="_blank" rel="noopener noreferrer" className="hover:text-bone">
                  {item.image.attribution.license}
                </a>
              </div>
            )}
          </div>
        )}
      </header>

      <div className="prose prose-invert prose-lg max-w-none">
        <div className="text-xl text-fog/95 mb-8 leading-relaxed border-l-2 border-gild/30 pl-6">
          {item.lede}
        </div>
        
        {item.analysis && (
          <div className="mb-8">
            <h2 className="font-serif text-2xl text-bone mb-4">Analysis</h2>
            <p className="text-fog/90 leading-relaxed">{item.analysis}</p>
          </div>
        )}
        
        <div className="grid md:grid-cols-2 gap-8 my-8">
          <div className="bg-ash/30 rounded-xl p-6 border border-white/5">
            <h3 className="font-serif text-xl text-bone mb-3">Why it matters</h3>
            <p className="text-fog/90 leading-relaxed">{item.why_it_matters}</p>
          </div>
          
          <div className="bg-alert/10 rounded-xl p-6 border border-alert/20">
            <h3 className="font-serif text-xl text-alert mb-3">Risk scenario</h3>
            <p className="text-bone/90 leading-relaxed">{item.risk_scenario}</p>
          </div>
        </div>
        
        <div className="mt-8 pt-6 border-t border-white/10">
          <h3 className="font-serif text-xl text-bone mb-4">Sources</h3>
          <ul className="space-y-2">
            {item.sources?.map((s, i) => {
              const source = typeof s === 'string' ? { title: `Source ${i + 1}`, url: s } : s;
              return (
                <li key={i}>
                  <a 
                    className="text-limewire hover:text-limewire/80 underline underline-offset-2" 
                    href={source.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                  >
                    {source.title}
                  </a>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </article>
  );
}
