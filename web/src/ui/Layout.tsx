import { PropsWithChildren } from "react";
import { TopNav } from "./TopNav";
import { LangToggle } from "./LangToggle";
import { useLanguage, link } from "../utils/lang";

export function Layout({ children }: PropsWithChildren) {
  const { lang } = useLanguage();
  
  return (
    <div className="min-h-screen bg-ink text-bone relative">
      {/* liminal overlays */}
      <div className="pointer-events-none fixed inset-0 bg-grain opacity-[0.07] mix-blend-soft-light" />
      <div className="pointer-events-none fixed inset-0 bg-grid bg-grid opacity-[0.06]" />

      <header className="sticky top-0 z-40 bg-ink/85 backdrop-blur border-b border-white/5">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <a href={link('/', lang)} className="font-serif text-xl tracking-[0.02em]">
            PARANOID<span className="text-gild">.</span>MODELS
          </a>
          <div className="flex items-center gap-6">
            <TopNav />
            <LangToggle />
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">{children}</main>

      <footer className="border-t border-white/5 mt-16">
        <div className="max-w-6xl mx-auto px-4 py-8 text-sm text-fog/80">
          © {new Date().getFullYear()} Paranoid Models — Intelligence, Counter-Narratives, Risk
        </div>
      </footer>
    </div>
  );
}
