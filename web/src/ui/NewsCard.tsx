import { motion } from "framer-motion";
import type { Card } from "../data/fetchFeed";
import { useLanguage, link } from "../utils/lang";
import { heroFor } from "../utils/hero";

export function NewsCard({ c }: { c: Card }) {
  const { lang } = useLanguage();
  
  // Use provided image or generate fallback
  const heroUrl = c.image?.card || heroFor(c.category);
  
  return (
    <motion.article
      initial={{ y: 10, opacity: 0 }}
      whileInView={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="group rounded-2xl border border-white/10 bg-ash/40 hover:bg-ash/60 shadow-soft overflow-hidden card-rgb"
    >
      {heroUrl && (
        <div className="relative h-48 overflow-hidden">
          <img
            src={heroUrl}
            alt=""
            className="w-full h-full object-cover scale-[1.03] group-hover:scale-[1.06] transition-transform duration-700"
            style={{ filter: "grayscale(100%) contrast(1.15) brightness(0.85)" }}
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
          {/* light vignette */}
          <div className="absolute inset-0 bg-gradient-to-t from-ink/80 via-transparent to-transparent" />
        </div>
      )}

      <div className="p-5 flex flex-col gap-2">
        <div className="text-[11px] tracking-widest uppercase text-gild">{c.kicker}</div>
        <h3 className="font-serif text-xl leading-snug">
          <a 
            href={link(`/article/${c.id}`, lang)} 
            className="hover:underline underline-offset-4 decoration-gild/60"
          >
            {c.headline}
          </a>
        </h3>
        <p className="text-fog/90">{c.lede}</p>

        <div className="mt-3 pt-3 border-t border-white/10 grid gap-2 text-sm">
          <div>
            <span className="text-fog/70">Why it matters: </span>
            <span className="text-bone">{c.why_it_matters}</span>
          </div>
          <div>
            <span className="text-fog/70">Risk scenario: </span>
            <span className="text-alert/90">{c.risk_scenario}</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {c.sources?.slice(0,3).map((s,i) => {
              const source = typeof s === 'string' ? { title: `Source ${i + 1}`, url: s } : s;
              return (
                <a 
                  key={i} 
                  href={source.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-[12px] text-limewire/90 hover:text-limewire underline underline-offset-2"
                >
                  {source.title}
                </a>
              );
            })}
          </div>
          
          {c.image?.attribution && (
            <div className="text-[10px] text-fog/50 pt-2 border-t border-white/5">
              Image: <a href={c.image.attribution.source_url} target="_blank" rel="noopener noreferrer" className="text-limewire/70 hover:text-limewire">{c.image.attribution.author}</a> / 
              <a href={c.image.attribution.license_url} target="_blank" rel="noopener noreferrer" className="text-limewire/70 hover:text-limewire">{c.image.attribution.license}</a>
            </div>
          )}
        </div>
      </div>
    </motion.article>
  );
}
