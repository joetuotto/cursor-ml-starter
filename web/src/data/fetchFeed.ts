import type { Lang } from "../utils/lang";

export type Card = {
  id: string;
  category?: string;     // 'geopolitics' | 'infoops' | ...
  kicker: string;
  headline: string;
  lede: string;
  analysis?: string;
  why_it_matters: string;
  risk_scenario: string;
  sources: { title: string; url: string }[] | string[];
  lang: Lang;
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
  _meta?: any;
};

export async function fetchFeed(lang: Lang, category?: string): Promise<Card[]> {
  // Try local first, fallback to GCS
  const localUrl = `/newswire/trends.${lang}.json`;
  const gcsUrl = `https://storage.googleapis.com/paranoidmodels.com/newswire/trends.${lang}.json`;
  
  try {
    const res = await fetch(localUrl, { cache: "no-store" });
    if (!res.ok) throw new Error('Local feed not found');
    const all: Card[] = await res.json();
    return filterAndProcess(all, category);
  } catch (error) {
    console.log('Falling back to GCS feed:', gcsUrl);
    const res = await fetch(gcsUrl, { cache: "no-store" });
    const all: Card[] = await res.json();
    return filterAndProcess(all, category);
  }
}

function filterAndProcess(cards: Card[], category?: string): Card[] {
  return cards
    .filter(c => category ? c.category === category : true)
    .map(c => ({
      ...c,
      // Normalize sources to object format
      sources: Array.isArray(c.sources) && typeof c.sources[0] === 'string' 
        ? (c.sources as string[]).map((url, i) => ({ title: `Source ${i + 1}`, url }))
        : c.sources as { title: string; url: string }[],
      // Add fallback category
      category: c.category || 'general'
    }));
}
