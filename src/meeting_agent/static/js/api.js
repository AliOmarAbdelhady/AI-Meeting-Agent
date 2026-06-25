// api.js — thin fetch wrapper around the REST API. Normalizes errors and 204s.

const BASE = "/api/v1";

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

async function request(path, { method = "GET", body, query } = {}) {
  let url = BASE + path;
  if (query) {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== "") params.append(k, v);
    }
    const qs = params.toString();
    if (qs) url += `?${qs}`;
  }

  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(url, opts);
  } catch (e) {
    throw new ApiError(`Network error: ${e.message}`, 0);
  }

  // 204 No Content (DELETE endpoints) — there is no JSON body.
  if (res.status === 204) return null;

  const text = await res.text();
  let data = null;
  if (text) {
    try { data = JSON.parse(text); } catch { data = text; }
  }

  if (!res.ok) {
    // The app returns {"error": {"code","message"}} (HTTP 400), FastAPI returns {"detail": ...}.
    const msg = data?.error?.message || data?.detail || `Request failed (${res.status})`;
    throw new ApiError(msg, res.status, data);
  }
  return data;
}

export const api = {
  // health & meta
  health: () => request("/health"),
  stats: () => request("/stats"),
  settingsInfo: () => request("/settings/info"),

  // meetings
  listMeetings: (query) => request("/meetings", { query }),
  getMeeting: (id) => request(`/meetings/${id}`),
  createMeeting: (body) => request("/meetings", { method: "POST", body }),
  updateMeeting: (id, body) => request(`/meetings/${id}`, { method: "PATCH", body }),
  deleteMeeting: (id) => request(`/meetings/${id}`, { method: "DELETE" }),
  startMeeting: (id) => request(`/meetings/${id}/start`, { method: "POST" }),
  stopMeeting: (id) => request(`/meetings/${id}/stop`, { method: "POST" }),
  meetingStatus: (id) => request(`/meetings/${id}/status`),
  meetingTranscript: (id) => request(`/meetings/${id}/transcript`),
  meetingSummary: (id) => request(`/meetings/${id}/summary`),
  meetingTasks: (id) => request(`/meetings/${id}/tasks`),
  meetingEmails: (id) => request(`/meetings/${id}/emails`),
  sendMeetingEmail: (id, body) => request(`/meetings/${id}/send-email`, { method: "POST", body }),

  // transcripts / summaries
  exportTranscript: (id, format) => request(`/transcripts/${id}/export`, { query: { format } }),
  updateSummary: (id, body) => request(`/summaries/${id}`, { method: "PATCH", body }),

  // tasks
  listTasks: (query) => request("/tasks", { query }),
  updateTask: (id, body) => request(`/tasks/${id}`, { method: "PATCH", body }),
  deleteTask: (id) => request(`/tasks/${id}`, { method: "DELETE" }),
};
