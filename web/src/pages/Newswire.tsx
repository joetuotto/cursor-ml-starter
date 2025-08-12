import React, { useEffect, useMemo, useState } from "react";
import NewsCard from "@/components/NewsCard";
import { CATEGORIES } from "@/config/categories";
import Header from "@/components/Header";

export default function Newswire() {
  const [lang, setLang] = useState<"en" | "fi">("en");
  const [items, setItems] = useState<any[]>([]);

  useEffect(() => {
    const url = lang === "en" ? "/feeds/trends.en.json" : "/feeds/trends.fi.json";
    fetch(url).then(r => r.json()).then(setItems).catch(()=>setItems([]));
  }, [lang]);

  const hash = typeof window !== "undefined" ? window.location.hash.replace("#","") : "";
  const activeKey = useMemo(() => {
    const ok = CATEGORIES.find(c => c.key === hash)?.key;
    return ok || "";
  }, [hash]);
  const filtered = useMemo(
    () => (activeKey ? items.filter(i => i?._meta?.category === activeKey) : items),
    [items, activeKey]
  );

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[#0B0F1A] via-black to-black">
      <Header lang={lang} onLangChange={setLang} />
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((item, idx) => <NewsCard key={idx} item={item} />)}
        </div>
      </div>
    </div>
  );
}
