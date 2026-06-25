// tasks.js — Kanban board of action items, with drag-to-move and edit/delete.
import { api } from "../api.js";
import { escapeHtml, formatDateTime, localToIso, LABELS } from "../utils.js";
import { priorityBadge } from "../components/badge.js";
import { pushToast, reportError } from "../components/toast.js";
import { openModal, confirmDialog } from "../components/modal.js";

const COLUMNS = ["pending", "in_progress", "completed", "cancelled"];
let tasks = [];

export async function render(container) {
  container.innerHTML = `<div class="loading"><div class="spinner"></div> Loading tasks…</div>`;
  try {
    const data = await api.listTasks({ page: 1, page_size: 200 });
    tasks = data.items || [];
    renderBoard(container);
  } catch (err) {
    container.innerHTML = `<div class="error-state">⚠️ Failed to load tasks: ${escapeHtml(err.message)}</div>`;
  }
}

function renderBoard(container) {
  container.innerHTML = `
    <div class="toolbar">
      <div class="muted">Drag cards between columns to update status, or use the <strong>edit</strong> button.</div>
    </div>
    <div class="kanban" id="kanban">
      ${COLUMNS.map((col) => `
        <div class="kanban-col" data-status="${col}">
          <div class="kanban-col-header">
            <span class="kanban-col-title">${escapeHtml(LABELS.status[col] || col)}</span>
            <span class="kanban-col-count" data-count="${col}">0</span>
          </div>
          <div class="kanban-cards" data-drop="${col}"></div>
        </div>`).join("")}
    </div>`;

  for (const col of COLUMNS) {
    const zone = container.querySelector(`[data-drop="${col}"]`);
    const colTasks = tasks.filter((t) => t.status === col);
    container.querySelector(`[data-count="${col}"]`).textContent = colTasks.length;
    zone.innerHTML = colTasks.map(taskCard).join("") || `<div class="faint" style="padding:8px 4px; font-size:13px;">No tasks</div>`;
  }

  wireCards(container);
  wireDropZones(container);
}

function taskCard(t) {
  return `<div class="task-card" draggable="true" data-id="${escapeHtml(t.id)}" data-priority="${escapeHtml(t.priority || "medium")}">
    <div class="tc-title">${escapeHtml(t.title)}</div>
    ${t.description ? `<div class="tc-desc">${escapeHtml(t.description)}</div>` : ""}
    <div class="tc-meta">
      ${priorityBadge(t.priority)}
      ${t.assignee_name ? `<span class="tc-assignee">👤 ${escapeHtml(t.assignee_name)}</span>` : ""}
      ${t.due_date ? `<span>📅 ${formatDateTime(t.due_date)}</span>` : ""}
    </div>
    <div class="tc-actions">
      <button class="btn btn-sm btn-ghost" data-act="edit">✏️ Edit</button>
      <button class="btn btn-sm btn-ghost" data-act="del">🗑</button>
    </div>
  </div>`;
}

function wireCards(container) {
  container.querySelectorAll(".task-card").forEach((card) => {
    const id = card.dataset.id;
    card.addEventListener("dragstart", () => card.classList.add("dragging"));
    card.addEventListener("dragend", () => card.classList.remove("dragging"));
    card.querySelector('[data-act="edit"]').addEventListener("click", (e) => { e.stopPropagation(); openEdit(id); });
    card.querySelector('[data-act="del"]').addEventListener("click", async (e) => {
      e.stopPropagation();
      const t = tasks.find((x) => x.id === id);
      if (await confirmDialog(`Delete task "${t?.title || id}"?`, { okText: "Delete", danger: true })) {
        try { await api.deleteTask(id); tasks = tasks.filter((x) => x.id !== id); renderBoard(container); pushToast("success", "Task deleted."); }
        catch (err) { reportError(err, "Could not delete task."); }
      }
    });
  });
}

function wireDropZones(container) {
  container.querySelectorAll("[data-drop]").forEach((zone) => {
    zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("drag-over"); });
    zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
    zone.addEventListener("drop", async (e) => {
      e.preventDefault();
      zone.classList.remove("drag-over");
      const id = e.dataTransfer.getData("text/plain") || container.querySelector(".dragging")?.dataset.id;
      if (!id) return;
      const newStatus = zone.dataset.drop;
      const t = tasks.find((x) => x.id === id);
      if (!t || t.status === newStatus) return;
      try {
        const updated = await api.updateTask(id, { status: newStatus });
        Object.assign(t, updated);
        renderBoard(container);
        pushToast("success", `Moved to ${LABELS.status[newStatus]}.`);
      } catch (err) { reportError(err, "Could not move task."); }
    });
  });
  // Make cards carry their id on drag.
  container.querySelectorAll(".task-card").forEach((card) => {
    card.addEventListener("dragstart", (e) => e.dataTransfer.setData("text/plain", card.dataset.id));
  });
}

function openEdit(id) {
  const t = tasks.find((x) => x.id === id);
  if (!t) return;
  const body = document.createElement("div");
  body.innerHTML = `
    <div class="form-grid">
      <div class="field full"><label class="label">Title</label><input class="input" id="t-title" value="${escapeHtml(t.title)}" /></div>
      <div class="field"><label class="label">Priority</label>
        <select class="select" id="t-priority">${["high", "medium", "low"].map((p) => `<option value="${p}" ${t.priority === p ? "selected" : ""}>${p}</option>`).join("")}</select></div>
      <div class="field"><label class="label">Status</label>
        <select class="select" id="t-status">${COLUMNS.map((s) => `<option value="${s}" ${t.status === s ? "selected" : ""}>${LABELS.status[s]}</option>`).join("")}</select></div>
      <div class="field"><label class="label">Assignee name</label><input class="input" id="t-name" value="${escapeHtml(t.assignee_name || "")}" /></div>
      <div class="field"><label class="label">Assignee email</label><input class="input" id="t-email" value="${escapeHtml(t.assignee_email || "")}" /></div>
      <div class="field"><label class="label">Due date</label><input class="input" id="t-due" type="datetime-local" /></div>
      <div class="field full"><label class="label">Description</label><textarea class="textarea" id="t-desc">${escapeHtml(t.description || "")}</textarea></div>
    </div>`;
  if (t.due_date) body.querySelector("#t-due").value = new Date(t.due_date).toISOString().slice(0, 16);

  openModal({
    title: "Edit task",
    body,
    actions: [
      { label: "Cancel" },
      { label: "Save", variant: "primary", onClick: async (modal) => {
        const due = body.querySelector("#t-due").value;
        const payload = {
          title: body.querySelector("#t-title").value.trim(),
          priority: body.querySelector("#t-priority").value,
          status: body.querySelector("#t-status").value,
          assignee_name: body.querySelector("#t-name").value.trim() || null,
          assignee_email: body.querySelector("#t-email").value.trim() || null,
          due_date: due ? localToIso(due) : null,
          description: body.querySelector("#t-desc").value.trim() || null,
        };
        const btn = modal.querySelector(".modal-footer button:last-child");
        btn.disabled = true; btn.textContent = "Saving…";
        try {
          const updated = await api.updateTask(id, payload);
          const idx = tasks.findIndex((x) => x.id === id);
          if (idx >= 0) tasks[idx] = { ...tasks[idx], ...updated };
          pushToast("success", "Task updated.");
          renderBoard(document.getElementById("view"));
          return true;
        } catch (err) { reportError(err, "Could not update task."); btn.disabled = false; btn.textContent = "Save"; return false; }
      } },
    ],
  });
}
