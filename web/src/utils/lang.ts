export type Lang = "en" | "fi";

export function detectLangFromPath(): Lang {
  const seg = location.pathname.split("/")[1];
  return seg === "fi" ? "fi" : "en";
}

export function useLanguage() {
  const lang = detectLangFromPath();
  const asHref = (to: Lang) => {
    const cur = location.pathname.replace(/^\/(en|fi)/,'');
    return `/${to}${cur || "/"}` + location.hash;
  };
  return { lang, asHref };
}

export function link(path: string, lang: Lang) {
  const clean = path.startsWith("/") ? path : `/${path}`;
  return `/${lang}${clean}`;
}
