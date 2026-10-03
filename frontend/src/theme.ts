const KEY = "intel2doc_theme";

export type Theme = "light" | "dark";

export function initTheme(): Theme {
  const t = (localStorage.getItem(KEY) as Theme) || "light";
  document.documentElement.dataset.theme = t;
  return t;
}

export function getTheme(): Theme {
  return (document.documentElement.dataset.theme as Theme) || "light";
}

export function setTheme(t: Theme) {
  document.documentElement.dataset.theme = t;
  localStorage.setItem(KEY, t);
}

export function toggleTheme(): Theme {
  const next: Theme = getTheme() === "dark" ? "light" : "dark";
  setTheme(next);
  return next;
}
