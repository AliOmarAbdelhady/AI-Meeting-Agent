// toast.js — transient notifications.
import { escapeHtml } from "../utils.js";

const ICONS = { success: "✅", error: "⚠️", info: "ℹ️", warning: "⚠️" };

/** Show a toast. type: success | error | info | warning */
export function pushToast(type, message) {
  const container = document.getElementById("toasts");
  if (!container) return;
  const t = document.createElement("div");
  t.className = `toast toast-${type}`;
  t.innerHTML = `<span class="toast-ico">${ICONS[type] || "ℹ️"}</span><span>${escapeHtml(message)}</span>`;
  container.appendChild(t);
  setTimeout(() => {
    t.classList.add("toast-hide");
    setTimeout(() => t.remove(), 260);
  }, 3800);
}

/** Convenience: report an error from any thrown value (esp. ApiError). */
export function reportError(err, fallback = "Something went wrong") {
  const msg = err?.message || fallback;
  pushToast("error", msg);
}
