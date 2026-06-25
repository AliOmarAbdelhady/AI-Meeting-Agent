// meetings.js — list, filter, search, paginate, create meetings.
import { api } from "../api.js";
import { escapeHtml, formatDateTime, debounce, localToIso, LABELS } from "../utils.js";
import { statusBadge } from "../components/badge.js";
import { pushToast, reportError } from "../components/toast.js";
import { openModal } from "../components/modal.js";
import { createTagsInput } from "../components/tags-input.js";
import { navigate } from "../router.js";

const state = { search: "", status: "", platform: "", page: 1, pageSize: 20 };

export async function render(container) {
  container.innerHTML = `
    <div class="toolbar">
      <div class="search-input">
        <input class="input" id="m-search" type="search" placeholder="Search meetings…" value="${escapeHtml(state.search)}" />
      </div>
      <select class="select" id="m-status">
        <option value="">All statuses</option>
        ${Object.entries(LABELS.status).map(([k, v]) => `<option value="${k}" ${state.status === k ? "selected" : ""}>${v}</option>`).join("")}
      </select>
      <select class="select" id="m-platform">
        <option value="">All platforms</option>
        ${Object.entries(LABELS.platform).map(([k, v]) => `<option value="${k}" ${state.platform === k ? "selected" : ""}>${v}</option>`).join("")}
      </select>
      <div class="spacer"></div>
      <button class="btn btn-primary" id="m-new">＋ New meeting</button>
    </div>
    <div class="card">
      <div id="m-table"><div class="loading"><div class="spinner"></div> Loading…</div></div>
    </div>`;

  const search = container.querySelector("#m-search");
  search.addEventListener("input", debounce((e) => { state.search = e.target.value; state.page = 1; loadTable(container); }, 250));
  container.querySelector("#m-status").addEventListener("change", (e) => { state.status = e.target.value; state.page = 1; loadTable(container); });
  container.querySelector("#m-platform").addEventListener("change", (e) => { state.platform = e.target.value; state.page = 1; loadTable(container); });
  container.querySelector("#m-new").addEventListener("click", () => openCreateModal(container));

  await loadTable(container);
}

async function loadTable(container) {
  const wrap = container.querySelector("#m-table");
  try {
    const data = await api.listMeetings({
      page: state.page, page_size: state.pageSize, status: state.status, platform: state.platform,
    });
    const items = data.items || [];
    if (!items.length) {
      wrap.innerHTML = `<div class="empty-state"><span class="emoji">🗓️</span>No meetings found.<br><span class="faint">Try adjusting filters or create a new meeting.</span></div>`;
      return;
    }

    wrap.innerHTML = `
      <table class="table">
        <thead><tr>
          <th class="col-grow">Title</th><th>Platform</th><th>Scheduled</th><th>Status</th><th></th>
        </tr></thead>
        <tbody>
          ${items.map((m) => `
            <tr class="row-link" data-id="${escapeHtml(m.id)}">
              <td><strong>${escapeHtml(m.title)}</strong><div class="cell-muted">${(m.participants || []).length} participant(s)</div></td>
              <td>${escapeHtml(LABELS.platform[m.platform] || m.platform)}</td>
              <td class="cell-muted">${formatDateTime(m.scheduled_at)}</td>
              <td>${statusBadge(m.status)}</td>
              <td class="faint nowrap">→</td>
            </tr>`).join("")}
        </tbody>
      </table>
      ${pagination(container, data)}`;
    wrap.querySelectorAll(".row-link").forEach((row) => {
      row.addEventListener("click", () => navigate(`#/meetings/${row.dataset.id}`));
    });
    const prev = wrap.querySelector("#m-prev");
    const next = wrap.querySelector("#m-next");
    if (prev) prev.addEventListener("click", () => { state.page--; loadTable(container); });
    if (next) next.addEventListener("click", () => { state.page++; loadTable(container); });
  } catch (err) {
    wrap.innerHTML = `<div class="error-state">⚠️ ${escapeHtml(err.message)}</div>`;
  }
}

function pagination(container, data) {
  const totalPages = Math.max(1, Math.ceil(data.total / state.pageSize));
  const prev = `<button class="btn btn-sm" id="m-prev" ${state.page <= 1 ? "disabled" : ""}>← Prev</button>`;
  const next = `<button class="btn btn-sm" id="m-next" ${state.page >= totalPages ? "disabled" : ""}>Next →</button>`;
  return `<div class="pagination">
    <span class="page-info">Page ${state.page} of ${totalPages} · ${data.total} total</span>
    <div class="btn-row">${prev}${next}</div>
  </div>`;
}

function openCreateModal(container) {
  const body = document.createElement("div");
  body.innerHTML = `
    <div class="form-grid">
      <div class="field full"><label class="label">Title</label><input class="input" id="f-title" placeholder="Sprint Planning" /></div>
      <div class="field"><label class="label">Platform</label>
        <select class="select" id="f-platform">
          ${Object.entries(LABELS.platform).map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}
        </select></div>
      <div class="field"><label class="label">Scheduled at</label><input class="input" id="f-scheduled" type="datetime-local" /></div>
      <div class="field full"><label class="label">Meeting URL</label><input class="input" id="f-url" placeholder="https://meet.google.com/abc-defg-hij" /></div>
      <div class="field full"><label class="label">Participants (emails)</label><div id="f-participants"></div></div>
    </div>`;
  const tags = createTagsInput([], { placeholder: "name@example.com, press Enter…" });
  body.querySelector("#f-participants").appendChild(tags.el);

  openModal({
    title: "Schedule new meeting",
    body,
    actions: [
      { label: "Cancel" },
      { label: "Create", variant: "primary", onClick: async (modal) => {
        const title = body.querySelector("#f-title").value.trim();
        const platform = body.querySelector("#f-platform").value;
        const scheduled = body.querySelector("#f-scheduled").value;
        const meetingUrl = body.querySelector("#f-url").value.trim();
        if (!title || !meetingUrl || !scheduled) { pushToast("warning", "Title, URL and scheduled time are required."); return false; }
        const submit = modal.querySelector(".modal-footer button:last-child");
        submit.disabled = true; submit.textContent = "Creating…";
        try {
          await api.createMeeting({
            title, platform, meeting_url: meetingUrl,
            scheduled_at: localToIso(scheduled),
            participants: tags.getValue(),
          });
          pushToast("success", "Meeting created.");
          await loadTable(container);
          return true;
        } catch (err) { reportError(err, "Could not create meeting."); submit.disabled = false; submit.textContent = "Create"; return false; }
      } },
    ],
  });
}

export { loadTable };
