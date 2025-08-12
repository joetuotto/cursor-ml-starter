import React from "react";
import { CATEGORIES } from "@/config/categories";

interface HeaderProps {
  lang: "en" | "fi";
  onLangChange?: (lang: "en" | "fi") => void;
}

const Header: React.FC<HeaderProps> = ({ lang, onLangChange }) => {
  return (
    <header className="sticky top-0 z-30 backdrop-blur supports-[backdrop-filter]:bg-black/50 border-b border-white/10">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <a href="/" className="font-semibold tracking-tight text-gray-200">
          Paranoid Newswire
        </a>

        <nav className="hidden sm:flex items-center gap-4 text-sm">
          {CATEGORIES.map(c => (
            <a
              key={c.key}
              href={`/newswire/${lang}/#${c.key}`}
              className="text-gray-300 hover:text-white transition-colors"
            >
              {lang === "fi" ? c.label_fi : c.label_en}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2 text-xs">
          <button
            type="button"
            onClick={() => onLangChange && onLangChange("en")}
            className={`px-2 py-1 rounded-md border ${lang === "en" ? "bg-white text-black border-white" : "border-white/10 text-gray-200"}`}
            aria-pressed={lang === "en"}
          >
            ENG
          </button>
          <button
            type="button"
            onClick={() => onLangChange && onLangChange("fi")}
            className={`px-2 py-1 rounded-md border ${lang === "fi" ? "bg-white text-black border-white" : "border-white/10 text-gray-200"}`}
            aria-pressed={lang === "fi"}
          >
            FI
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;


