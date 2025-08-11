import { useLanguage } from "../utils/lang";

export function LangToggle() {
  const { lang, asHref } = useLanguage();
  const next = lang === "en" ? "fi" : "en";
  return (
    <a
      href={asHref(next)}
      className="text-sm border border-white/10 px-2 py-1 rounded hover:border-white/30 transition-colors"
    >
      {lang.toUpperCase()} ▸ {next.toUpperCase()}
    </a>
  );
}
