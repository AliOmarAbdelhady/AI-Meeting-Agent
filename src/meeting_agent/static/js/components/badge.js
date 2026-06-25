// badge.js — status & priority badges.
import { escapeHtml, LABELS } from "../utils.js";

const ACTIVE_STATUSES = new Set(["joining", "in_progress", "recording", "transcribing", "summarizing"]);

/** A badge for a meeting lifecycle status. */
export function statusBadge(status) {
  const label = LABELS.status[status] || status;
  const pulse = ACTIVE_STATUSES.has(status) ? " badge-pulse" : "";
  return `<span class="badge badge-${status}${pulse}">${escapeHtml(label)}</span>`;
}

/** A badge for a task priority. */
export function priorityBadge(priority) {
  const label = priority.charAt(0).toUpperCase() + priority.slice(1);
  return `<span class="badge badge-${priority}">${escapeHtml(label)}</span>`;
}

/** Small inline status pill for tasks. */
export function taskStatusBadge(status) {
  return `<span class="badge badge-${status}">${escapeHtml(LABELS.status[status] || status)}</span>`;
}
