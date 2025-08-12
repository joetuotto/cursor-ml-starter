import { useLanguage, link } from "../utils/lang";

const CATS = [
  { k: "geopolitics", label: "Geopolitics" },
  { k: "infoops", label: "Information Operations" },
  { k: "espionage", label: "Espionage & Intelligence" },
  { k: "highpolitics", label: "High Politics" },
  { k: "secrethistory", label: "Secret History" },
  { k: "elite", label: "Elite Analysis" },
  { k: "special", label: "Special Reports" },
];

export function TopNav() {
  const { lang } = useLanguage();
  
  return (
    <nav className="hidden md:flex items-center gap-4">
      <a
        href={link('/newswire', lang)}
        className="text-sm text-fog/90 hover:text-bone transition-colors"
      >
        Newswire
      </a>
      {CATS.map(c => (
        <a
          key={c.k}
          href={link(`/category/${c.k}`, lang)}
          className="text-sm text-fog/90 hover:text-bone transition-colors"
        >
          {c.label}
        </a>
      ))}
    </nav>
  );
}
