// meeting-detail.js — single meeting view with tabs + live status polling.
import { api } from "../api.js";
import {
  escapeHtml, formatDateTime, formatDuration, tsClock, localToIso, isoToLocal, debounce, poll, downloadText, LABELS,
} from "../utils.js";
import { statusBadge, priorityBadge, taskStatusBadge } from "../components/badge.js";
import { pushToast, reportError } from "../components/toast.js";
import { openModal, confirmDialog } from "../components/modal.js";
import { createTagsInput } from "../components/tags-input.js";
import { navigate } from "../router.js";

const ACTIVE = new Set(["joining", "in_progress", "recording", "transcribing", "summarizing"]);
const TABS = ["overview", "transcript", "summary", "tasks", "emails"];

let meeting = null;
let currentTab = "overview";
let poller = null;

export async function render(container, params) {
  const id = params.id;
  currentTab = params.tab || "overview";
  container.innerHTML = `<div class="loading"><div class="spinner"></div> Loading meeting…</div>`;
  try {
    meeting = await api.getMeeting(id);
  } catch (err) {
    container.innerHTML = `<div class="error-state">⚠️ Could not load meeting: ${escapeHtml(err.message)}</div>`;
    return;
  }
  updateTitle();
  renderShell(container, id);
  await loadTab(container, id);
  maybePoll(container, id);
}

function updateTitle() {
  const el = document.getElementById("page-title");
  if (el && meeting) el.textContent = meeting.title;
}

function renderShell(container, id) {
  container.innerHTML = `
    <div class="detail-header">
      <div>
        <div class="detail-title">${escapeHtml(meeting.title)} <span id="d-status">${statusBadge(meeting.status)}</span></div>
        <div class="detail-sub">
          <span>${escapeHtml(LABELS.platform[meeting.platform] || meeting.platform)}</span>
          <a href="${escapeHtml(meeting.meeting_url)}" target="_blank" rel="noopener">${escapeHtml(meeting.meeting_url)}</a>
          <span>📅 ${formatDateTime(meeting.scheduled_at)}</span>
        </div>
        ${meeting.error_message ? `<div class="error-state" style="padding:12px; text-align:left;">⚠️ ${escapeHtml(meeting.error_message)}</div>` : ""}
      </div>
      <div class="btn-row" id="d-actions"></div>
    </div>
    <div class="tabs" id="d-tabs">
      ${TABS.map((t) => `<button class="tab ${t === currentTab ? "active" : ""}" data-tab="${t}">${tabLabel(t)}</button>`).join("")}
    </div>
    <div id="d-tab-content"></div>`;

  // Tab switching
  container.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => navigate(`#/meetings/${id}/${btn.dataset.tab}`));
  });
  renderActions(container, id);
}

function tabLabel(t) {
  return { overview: "📋 Overview", transcript: "📝 Transcript", summary: "✨ Summary", tasks: "✅ Tasks", emails: "✉️ Emails" }[t] || t;
}

function renderActions(container, id) {
  const el = container.querySelector("#d-actions");
  const status = meeting.status;
  el.innerHTML = `
    ${status === "scheduled" ? `<button class="btn btn-primary" data-act="start">▶ Start</button>` : ""}
    ${["in_progress", "recording"].includes(status) ? `<button class="btn btn-danger" data-act="stop">■ Stop</button>` : ""}
    <button class="btn" data-act="email">✉️ Send email</button>
    <button class="btn" data-act="edit">✏️ Edit</button>
    ${["scheduled", "cancelled"].includes(status) ? `<button class="btn btn-ghost" data-act="del">🗑</button>` : ""}`;

  el.querySelector('[data-act="start"]')?.addEventListener("click", () => lifecycle(container, id, "start"));
  el.querySelector('[data-act="stop"]')?.addEventListener("click", () => lifecycle(container, id, "stop"));
  el.querySelector('[data-act="email"]')?.addEventListener("click", () => openEmailModal(container, id));
  el.querySelector('[data-act="edit"]')?.addEventListener("click", () => openEditModal(container, id));
  el.querySelector('[data-act="del"]')?.addEventListener("click", async () => {
    if (await confirmDialog(`Delete "${meeting.title}"?`, { okText: "Delete", danger: true })) {
      try { await api.deleteMeeting(id); pushToast("success", "Meeting deleted."); navigate("#/meetings"); }
      catch (err) { reportError(err, "Could not delete meeting."); }
    }
  });
}

async function lifecycle(container, id, action) {
  try {
    meeting = action === "start" ? await api.startMeeting(id) : await api.stopMeeting(id);
    container.querySelector("#d-status").innerHTML = statusBadge(meeting.status);
    renderActions(container, id);
    pushToast("success", action === "start" ? "Meeting started — bot is joining." : "Meeting stopped — processing began.");
    maybePoll(container, id);
  } catch (err) { reportError(err); }
}

function maybePoll(container, id) {
  if (poller) { poller.stop(); poller = null; }
  if (!ACTIVE.has(meeting.status)) return;
  poller = poll(async () => {
    try {
      const { status } = await api.meetingStatus(id);
      if (status !== meeting.status) {
        const wasActive = ACTIVE.has(meeting.status);
        meeting.status = status;
        container.querySelector("#d-status").innerHTML = statusBadge(status);
        renderActions(container, id);
        if (wasActive && !ACTIVE.has(status)) {
          pushToast("info", `Meeting is now ${LABELS.status[status]}.`);
          if (["completed"].includes(status)) loadTab(container, id); // refresh tab data
        }
      }
    } catch { /* best-effort */ }
  }, 3000);
}

async function loadTab(container, id) {
  const el = container.querySelector("#d-tab-content");
  el.innerHTML = `<div class="loading"><div class="spinner"></div> Loading…</div>`;
  try {
    if (currentTab === "overview") await renderOverview(el, id);
    else if (currentTab === "transcript") await renderTranscript(el, id);
    else if (currentTab === "summary") await renderSummary(el, id);
    else if (currentTab === "tasks") await renderTasks(el, id);
    else if (currentTab === "emails") await renderEmails(el, id);
  } catch (err) {
    el.innerHTML = `<div class="error-state">⚠️ ${escapeHtml(err.message)}</div>`;
  }
}

// ── Overview tab ──────────────────────────────────────────
async function renderOverview(el, id) {
  const dt = (label, val) => `<dt>${label}</dt><dd>${val ?? "—"}</dd>`;
  el.innerHTML = `
    <div class="card card-pad">
      <dl class="kv-list">
        ${dt("Status", statusBadge(meeting.status))}
        ${dt("Platform", escapeHtml(LABELS.platform[meeting.platform] || meeting.platform))}
        ${dt("Scheduled", formatDateTime(meeting.scheduled_at))}
        ${dt("Started", formatDateTime(meeting.started_at))}
        ${dt("Ended", formatDateTime(meeting.ended_at))}
        ${dt("Duration", formatDuration(meeting.duration_seconds))}
        ${dt("Participants", (meeting.participants || []).length ? meeting.participants.map(escapeHtml).join(", ") : "—")}
      </dl>
    </div>`;
}

// ── Transcript tab ────────────────────────────────────────
async function renderTranscript(el, id) {
  let transcript;
  try { transcript = await api.meetingTranscript(id); }
  catch (err) {
    if (err.status === 404) {
      el.innerHTML = `<div class="empty-state"><span class="emoji">⏳</span>Transcript not ready yet.<br><span class="faint">It appears here once the meeting is transcribed.</span></div>`;
      return;
    }
    throw err;
  }
  const segs = transcript.segments || [];
  const searchInput = `<div class="toolbar"><div class="search-input"><input class="input" id="tr-search" type="search" placeholder="Search transcript…" /></div>
    <div class="spacer"></div>
    <div class="btn-row">
      <button class="btn btn-sm" data-fmt="txt">⬇ TXT</button>
      <button class="btn btn-sm" data-fmt="srt">⬇ SRT</button>
      <button class="btn btn-sm" data-fmt="vtt">⬇ VTT</button>
    </div></div>`;
  el.innerHTML = `
    ${searchInput}
    <div class="card card-pad">
      <div class="muted mb" style="font-size:13px;">${segs.length} segments · ${formatDuration(transcript.duration_seconds)} · language ${escapeHtml(transcript.language || "en")}</div>
      <div class="transcript-segments" id="tr-segs">
        ${segs.map((s) => `<div class="segment">
          <span class="ts" data-start="${s.start_time}">${tsClock(s.start_time)}</span>
          <span class="seg-text">${s.speaker ? `<span class="speaker">${escapeHtml(s.speaker)}</span>` : ""}${escapeHtml(s.text)}</span>
        </div>`).join("") || `<div class="muted">No segments.</div>`}
      </div>
    </div>`;

  const search = el.querySelector("#tr-search");
  const segEls = el.querySelectorAll(".segment");
  search.addEventListener("input", debounce((e) => {
    const q = e.target.value.trim().toLowerCase();
    segEls.forEach((seg) => {
      const text = seg.querySelector(".seg-text").textContent.toLowerCase();
      seg.style.display = !q || text.includes(q) ? "" : "none";
    });
  }, 200));

  el.querySelectorAll("[data-fmt]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        const exp = await api.exportTranscript(transcript.id, btn.dataset.fmt);
        const mime = btn.dataset.fmt === "txt" ? "text/plain" : btn.dataset.fmt === "srt" ? "application/x-subrip" : "text/vtt";
        downloadText(exp.filename, exp.content, mime);
        pushToast("success", `Exported ${exp.filename}`);
      } catch (err) { reportError(err, "Export failed."); }
    });
  });
}

// ── Summary tab ───────────────────────────────────────────
async function renderSummary(el, id) {
  let summary;
  try { summary = await api.meetingSummary(id); }
  catch (err) {
    if (err.status === 404) {
      el.innerHTML = `<div class="empty-state"><span class="emoji">⏳</span>Summary not ready yet.<br><span class="faint">It appears here once the meeting is summarized.</span></div>`;
      return;
    }
    throw err;
  }
  const list = (items) => (items?.length ? `<ul class="bullet-list">${items.map(escapeHtml).map((i) => `<li>${i}</li>`).join("")}</ul>` : `<span class="faint">None</span>`);
  el.innerHTML = `
    <div class="dashboard-grid">
      <div class="card card-pad">
        <div class="flex between center mb"><span class="card-title">Summary</span>
          <button class="btn btn-sm" id="sum-edit">✏️ Edit</button></div>
        <div class="summary-text">${escapeHtml(summary.summary_text)}</div>
      </div>
      <div class="flex" style="flex-direction:column; gap:16px;">
        <div class="card card-pad"><div class="section-title">🔑 Key points</div>${list(summary.key_points)}</div>
        <div class="card card-pad"><div class="section-title">✅ Decisions</div>${list(summary.decisions)}</div>
      </div>
    </div>
    <div class="card card-pad mt"><div class="section-title">📝 Action items</div>${list(summary.action_items)}</div>
    <div class="faint mt" style="font-size:12px;">Generated with ${escapeHtml(summary.model_used)} · ${summary.prompt_tokens ?? "?"}/${summary.completion_tokens ?? "?"} tokens</div>`;

  el.querySelector("#sum-edit").addEventListener("click", () => openSummaryEdit(id, summary, el));
}

function openSummaryEdit(id, summary, el) {
  const body = document.createElement("div");
  const toText = (arr) => (arr || []).join("\n");
  body.innerHTML = `
    <div class="field mb"><label class="label">Summary text</label><textarea class="textarea" id="s-text" style="min-height:140px;">${escapeHtml(summary.summary_text)}</textarea></div>
    <div class="field mb"><label class="label">Key points (one per line)</label><textarea class="textarea" id="s-key">${escapeHtml(toText(summary.key_points))}</textarea></div>
    <div class="field mb"><label class="label">Decisions (one per line)</label><textarea class="textarea" id="s-dec">${escapeHtml(toText(summary.decisions))}</textarea></div>
    <div class="field"><label class="label">Action items (one per line)</label><textarea class="textarea" id="s-act">${escapeHtml(toText(summary.action_items))}</textarea></div>`;
  const lines = (v) => v.split("\n").map((s) => s.trim()).filter(Boolean);
  openModal({
    title: "Edit summary",
    body,
    actions: [
      { label: "Cancel" },
      { label: "Save", variant: "primary", onClick: async (modal) => {
        const btn = modal.querySelector(".modal-footer button:last-child");
        btn.disabled = true; btn.textContent = "Saving…";
        try {
          const updated = await api.updateSummary(summary.id, {
            summary_text: body.querySelector("#s-text").value,
            key_points: lines(body.querySelector("#s-key").value),
            decisions: lines(body.querySelector("#s-dec").value),
            action_items: lines(body.querySelector("#s-act").value),
          });
          Object.assign(summary, updated);
          pushToast("success", "Summary saved.");
          await renderSummary(el, id);
          return true;
        } catch (err) { reportError(err); btn.disabled = false; btn.textContent = "Save"; return false; }
      } },
    ],
  });
}

// ── Tasks tab ─────────────────────────────────────────────
async function renderTasks(el, id) {
  const items = await api.meetingTasks(id);
  if (!items.length) {
    el.innerHTML = `<div class="empty-state"><span class="emoji">✅</span>No action items extracted.<br><span class="faint">Tasks appear here after the meeting is summarized.</span></div>`;
    return;
  }
  el.innerHTML = `<div class="card card-pad"><div class="list-cards">${items.map((t) => `
    <div class="task-card" data-priority="${escapeHtml(t.priority || "medium")}" data-id="${escapeHtml(t.id)}">
      <div class="flex between center"><div class="tc-title">${escapeHtml(t.title)}</div>${priorityBadge(t.priority)}</div>
      ${t.description ? `<div class="tc-desc">${escapeHtml(t.description)}</div>` : ""}
      <div class="tc-meta">
        ${taskStatusBadge(t.status)}
        ${t.assignee_name ? `<span>👤 ${escapeHtml(t.assignee_name)}</span>` : ""}
        ${t.due_date ? `<span>📅 ${formatDateTime(t.due_date)}</span>` : ""}
      </div>
      <div class="tc-actions">
        <select class="select btn-sm" data-id="${escapeHtml(t.id)}" style="width:auto;">
          ${["pending", "in_progress", "completed", "cancelled"].map((s) => `<option value="${s}" ${t.status === s ? "selected" : ""}>${LABELS.status[s]}</option>`).join("")}
        </select>
        <a href="#/tasks" class="btn btn-sm btn-ghost">Open board →</a>
      </div>
    </div>`).join("")}</div></div>`;

  el.querySelectorAll("select[data-id]").forEach((sel) => {
    sel.addEventListener("change", async () => {
      try { await api.updateTask(sel.dataset.id, { status: sel.value }); pushToast("success", "Task updated."); }
      catch (err) { reportError(err); }
    });
  });
}

// ── Emails tab ────────────────────────────────────────────
async function renderEmails(el, id) {
  const logs = await api.meetingEmails(id);
  el.innerHTML = `
    <div class="card card-pad mb">
      <div class="flex between center"><span class="card-title">Send summary email</span></div>
      <p class="muted" style="margin:8px 0 0; font-size:13px;">Requires a generated summary and a configured email provider.</p>
      <button class="btn btn-primary mt" id="em-compose">✉️ Compose email</button>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">Email history</span></div>
      ${logs.length ? `<table class="table"><thead><tr><th>Subject</th><th>Recipients</th><th>Status</th><th>Sent</th></tr></thead>
        <tbody>${logs.map((l) => `<tr>
          <td>${escapeHtml(l.subject)}</td>
          <td class="cell-muted">${escapeHtml((l.recipients || []).join(", "))}</td>
          <td><span class="badge badge-${l.status}">${escapeHtml(l.status)}</span></td>
          <td class="cell-muted">${formatDateTime(l.sent_at || l.created_at)}</td>
        </tr>`).join("")}</tbody></table>` : `<div class="empty-state"><span class="emoji">✉️</span>No emails sent yet.</div>`}
    </div>`;
  el.querySelector("#em-compose").addEventListener("click", () => openEmailModal(document.getElementById("view"), id));
}

function openEmailModal(container, id) {
  const body = document.createElement("div");
  body.innerHTML = `
    <div class="field mb"><label class="label">Recipients</label><div id="em-recipients"></div></div>
    <div class="field"><label class="label">Custom message (optional)</label><textarea class="textarea" id="em-msg" placeholder="Add a personal note…"></textarea></div>`;
  const tags = createTagsInput(meeting?.participants || [], { placeholder: "recipient@example.com, press Enter…" });
  body.querySelector("#em-recipients").appendChild(tags.el);
  openModal({
    title: "Send summary email",
    body,
    actions: [
      { label: "Cancel" },
      { label: "Send", variant: "primary", onClick: async (modal) => {
        const recipients = tags.getValue();
        if (!recipients.length) { pushToast("warning", "Add at least one recipient."); return false; }
        const btn = modal.querySelector(".modal-footer button:last-child");
        btn.disabled = true; btn.textContent = "Sending…";
        try {
          await api.sendMeetingEmail(id, { recipients, custom_message: body.querySelector("#em-msg").value.trim() || null });
          pushToast("success", "Email sent.");
          if (currentTab === "emails") await loadTab(container, id);
          return true;
        } catch (err) { reportError(err, "Email failed."); btn.disabled = false; btn.textContent = "Send"; return false; }
      } },
    ],
  });
}

function openEditModal(container, id) {
  const body = document.createElement("div");
  body.innerHTML = `
    <div class="form-grid">
      <div class="field full"><label class="label">Title</label><input class="input" id="e-title" value="${escapeHtml(meeting.title)}" /></div>
      <div class="field"><label class="label">Scheduled at</label><input class="input" id="e-scheduled" type="datetime-local" value="${isoToLocal(meeting.scheduled_at)}" /></div>
      <div class="field full"><label class="label">Participants</label><div id="e-participants"></div></div>
    </div>`;
  const tags = createTagsInput(meeting.participants || []);
  body.querySelector("#e-participants").appendChild(tags.el);
  openModal({
    title: "Edit meeting",
    body,
    actions: [
      { label: "Cancel" },
      { label: "Save", variant: "primary", onClick: async (modal) => {
        const btn = modal.querySelector(".modal-footer button:last-child");
        btn.disabled = true; btn.textContent = "Saving…";
        try {
          meeting = await api.updateMeeting(id, {
            title: body.querySelector("#e-title").value.trim(),
            scheduled_at: localToIso(body.querySelector("#e-scheduled").value),
            participants: tags.getValue(),
          });
          updateTitle();
          renderShell(container, id);
          await loadTab(container, id);
          pushToast("success", "Meeting updated.");
          return true;
        } catch (err) { reportError(err); btn.disabled = false; btn.textContent = "Save"; return false; }
      } },
    ],
  });
}

// Called by the router when navigating away, to stop polling.
export function cleanup() {
  if (poller) { poller.stop(); poller = null; }
}
