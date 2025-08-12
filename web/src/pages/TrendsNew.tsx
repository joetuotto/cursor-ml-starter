import { useEffect, useState } from "react";
import { useLanguage } from "../utils/lang";
import { fetchFeed, Card } from "../data/fetchFeed";
import { NewsCard } from "../ui/NewsCard";

export default function TrendsNew({ category }: { category?: string }) {
  const { lang } = useLanguage();
  const [data, setData] = useState<Card[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => { 
    setLoading(true);
    fetchFeed(lang, category)
      .then(setData)
      .finally(() => setLoading(false));
  }, [lang, category]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-fog/70">Loading intelligence reports...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {category && (
        <div className="border-b border-white/10 pb-4">
          <h1 className="font-serif text-3xl capitalize">{category.replace(/([A-Z])/g, ' $1').trim()}</h1>
          <p className="text-fog/80 mt-2">Intelligence analysis and risk assessment</p>
        </div>
      )}
      
      <div className="grid gap-6 md:grid-cols-2">
        {data.map(c => <NewsCard key={c.id} c={c} />)}
        {!data.length && (
          <div className="col-span-2 text-center py-16 text-fog/70">
            No intelligence reports available for this category.
          </div>
        )}
      </div>
    </div>
  );
}
