// utils.js — small DOM + formatting helpers shared across the app.

/** Escape a string for safe insertion as HTML text. */
export function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export const qs = (sel, root = document) => root.querySelector(sel);
export const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

/** Format an ISO timestamp to a local, human-readable date/time. */
export function formatDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

/** Relative time like "in 2h", "3 days ago". */
export function formatRelative(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  const diff = d - Date.now();
  const abs = Math.abs(diff);
  const min = 60 * 1000, hr = 60 * min, day = 24 * hr;
  let txt;
  if (abs < hr) txt = `${Math.round(abs / min)}m`;
  else if (abs < day) txt = `${Math.round(abs / hr)}h`;
  else txt = `${Math.round(abs / day)}d`;
  return diff >= 0 ? `in ${txt}` : `${txt} ago`;
}

/** Seconds -> "1h 23m" / "12m 30s". */
export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return "—";
  const s = Math.round(Number(seconds));
  if (!isFinite(s) || s < 0) return "—";
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h) return `${h}h ${m}m`;
  if (m) return `${m}m ${sec}s`;
  return `${sec}s`;
}

/** seconds -> "MM:SS" (for transcript timestamps). */
export function tsClock(seconds) {
  const s = Math.max(0, Math.floor(Number(seconds) || 0));
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

/** Convert a local <input type="datetime-local"> value to an ISO string. */
export function localToIso(local) {
  if (!local) return null;
  const d = new Date(local);
  return isNaN(d) ? null : d.toISOString();
}

/** Convert an ISO string to a value suitable for datetime-local input. */
export function isoToLocal(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return "";
  const off = d.getTimezoneOffset();
  return new Date(d.getTime() - off * 60000).toISOString().slice(0, 16);
}

export function debounce(fn, ms = 300) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

/** Repeatedly call fn every intervalMs until stop() is called. Returns { stop }. */
export function poll(fn, intervalMs) {
  let stopped = false;
  const run = async () => {
    if (stopped) return;
    try { await fn(); } catch { /* swallow; polling is best-effort */ }
    if (!stopped) setTimeout(run, intervalMs);
  };
  setTimeout(run, intervalMs);
  return { stop: () => { stopped = true; } };
}

/** Basic email validity check. */
export function isValidEmail(s) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(s).trim());
}

/** Trigger a client-side download of text content. */
export function downloadText(filename, content, mime = "text/plain") {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Friendly labels for enum values. */
export const LABELS = {
  platform: { google_meet: "Google Meet", zoom: "Zoom", teams: "Teams", other: "Other" },
  status: {
    scheduled: "Scheduled", joining: "Joining", in_progress: "In Progress",
    recording: "Recording", transcribing: "Transcribing", summarizing: "Summarizing",
    completed: "Completed", failed: "Failed", cancelled: "Cancelled",
  },
};
