// state.js — theme management + tiny pub/sub cache.

const THEME_KEY = "theme";

export function getTheme() {
  try { return localStorage.getItem(THEME_KEY) || "dark"; } catch { return "dark"; }
}

export function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem(THEME_KEY, theme); } catch { /* ignore */ }
  document.dispatchEvent(new CustomEvent("themechange", { detail: theme }));
}

export function toggleTheme() {
  setTheme(getTheme() === "dark" ? "light" : "dark");
}

/** Minimal subscribe/notify store for cross-view caches. */
export const store = {
  _subs: new Set(),
  _data: {},
  get(key) { return this._data[key]; },
  set(key, value) {
    this._data[key] = value;
    this._subs.forEach((fn) => fn(key, value));
  },
  subscribe(fn) {
    this._subs.add(fn);
    return () => this._subs.delete(fn);
  },
};
