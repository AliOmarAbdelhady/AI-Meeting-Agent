// app.js — entry point. Wires theme toggle + router, then renders the first route.
import { handleRoute } from "./router.js";
import { getTheme, toggleTheme } from "./state.js";

function setThemeIcon() {
  const btn = document.getElementById("theme-toggle");
  if (btn) btn.textContent = getTheme() === "dark" ? "☀️" : "🌙";
}

function init() {
  setThemeIcon();
  document.getElementById("theme-toggle")?.addEventListener("click", () => {
    toggleTheme();
    setThemeIcon();
  });

  window.addEventListener("hashchange", handleRoute);
  // Initial route (default to dashboard when hash is empty).
  if (!location.hash) location.hash = "#/dashboard";
  handleRoute();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
