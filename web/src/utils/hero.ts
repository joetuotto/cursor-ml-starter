const LIB: Record<string,string[]> = {
  geopolitics: [
    "https://images.unsplash.com/photo-1555949963-aa79dcee981d?q=80&w=2000&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1523731407965-2430cd12f5e4?q=80&w=2000&auto=format&fit=crop",
  ],
  infoops: [
    "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?q=80&w=2000&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1551281041-7f9b8839f911?q=80&w=2000&auto=format&fit=crop",
  ],
  espionage: [
    "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?q=80&w=2000&auto=format&fit=crop",
  ],
  highpolitics: [
    "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?q=80&w=2000&auto=format&fit=crop",
  ],
  secrethistory: [
    "https://images.unsplash.com/photo-1519681393784-d120267933ba?q=80&w=2000&auto=format&fit=crop",
  ],
  elite: [
    "https://images.unsplash.com/photo-1516637090014-cb1ab0d08fc7?q=80&w=2000&auto=format&fit=crop",
  ],
  special: [
    "https://images.unsplash.com/photo-1538688423619-a81d3f23454b?q=80&w=2000&auto=format&fit=crop",
  ],
};

export function heroFor(category?: string) {
  const pool = category && LIB[category] ? LIB[category] : Object.values(LIB).flat();
  return pool[Math.floor(Math.random()*pool.length)];
}
