// dashboard.js — overview tiles, status breakdown, recent meetings.
import { api } from "../api.js";
import { escapeHtml, formatDateTime, formatRelative, LABELS } from "../utils.js";
import { statusBadge } from "../components/badge.js";
import { navigate } from "../router.js";

function statCard(ico, value, label, accent = "") {
  return `<div class="stat-card">
    <span class="stat-ico">${ico}</span>
    <div class="stat-value ${accent}">${value}</div>
    <div class="stat-label">${label}</div>
  </div>`;
}

function statusBars(meetings) {
  const max = Math.max(1, ...Object.values(meetings));
  const order = ["scheduled", "joining", "in_progress", "recording", "transcribing", "summarizing", "completed", "failed", "cancelled"];
  return order.map((s) => {
    const n = meetings[s] || 0;
    const pct = Math.round((n / max) * 100);
    return `<div class="status-bar-row">
      ${statusBadge(s)}
      <div class="status-bar-track"><div class="status-bar-fill" style="width:${pct}%"></div></div>
      <span class="num">${n}</span>
    </div>`;
  }).join("");
}

export async function render(container) {
  container.innerHTML = `<div class="loading"><div class="spinner"></div> Loading dashboard…</div>`;
  try {
    const [stats, recent] = await Promise.all([
      api.stats(),
      api.listMeetings({ page: 1, page_size: 6 }),
    ]);

    const m = stats.meetings || {};
    const t = stats.tasks || {};
    const upcoming = (m.scheduled || 0) + (m.joining || 0);

    container.innerHTML = `
      <div class="stats-grid">
        ${statCard("📅", stats.meetings_total ?? 0, "Total meetings", "stat-accent")}
        ${statCard("⏰", upcoming, "Upcoming / active")}
        ${statCard("✅", m.completed || 0, "Completed")}
        ${statCard("📋", stats.tasks_total ?? 0, "Total tasks", "stat-accent")}
        ${statCard("🔄", t.pending || 0, "Pending tasks")}
      </div>

      <div class="dashboard-grid">
        <div class="card">
          <div class="card-header">
            <span class="card-title">Meeting status breakdown</span>
            <a href="#/meetings" class="btn btn-sm btn-ghost">View all →</a>
          </div>
          <div class="card-pad">
            <div class="status-bars">${statusBars(m)}</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><span class="card-title">Recent meetings</span></div>
          <div class="card-pad" id="recent-meetings"></div>
        </div>
      </div>`;

    const recentEl = container.querySelector("#recent-meetings");
    const items = recent?.items || [];
    if (!items.length) {
      recentEl.innerHTML = `<div class="empty-state"><span class="emoji">🗓️</span>No meetings yet.<br><a href="#/meetings">Schedule your first meeting →</a></div>`;
    } else {
      recentEl.innerHTML = `<div class="flex" style="flex-direction:column;">` + items.map((mt) => `
        <div class="row-link" data-id="${escapeHtml(mt.id)}" style="padding:11px 4px; border-bottom:1px solid var(--border);">
          <div class="flex between center gap-sm">
            <strong class="truncate" style="max-width:230px;">${escapeHtml(mt.title)}</strong>
            ${statusBadge(mt.status)}
          </div>
          <div class="muted" style="font-size:12.5px; margin-top:3px;">
            ${escapeHtml(LABELS.platform[mt.platform] || mt.platform)} · ${formatRelative(mt.scheduled_at)}
          </div>
        </div>`).join("") + `</div>`;
      recentEl.querySelectorAll(".row-link").forEach((row) => {
        row.addEventListener("click", () => navigate(`#/meetings/${row.dataset.id}`));
      });
    }
  } catch (err) {
    container.innerHTML = `<div class="error-state">⚠️ Failed to load dashboard: ${escapeHtml(err.message)}</div>`;
  }
}
