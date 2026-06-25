// router.js — hash-based router. Parses location.hash -> view module.
import * as dashboard from "./views/dashboard.js";
import * as meetings from "./views/meetings.js";
import * as meetingDetail from "./views/meeting-detail.js";
import * as tasks from "./views/tasks.js";
import * as settings from "./views/settings.js";

const routes = [
  { pattern: /^\/(dashboard)?\/?$/, view: dashboard, title: "Dashboard", nav: "dashboard" },
  { pattern: /^\/meetings\/?$/, view: meetings, title: "Meetings", nav: "meetings" },
  { pattern: /^\/meetings\/([^/]+)\/([^/?]+)\/?$/, view: meetingDetail, title: "Meeting", nav: "meetings", params: (m) => ({ id: decodeURIComponent(m[1]), tab: decodeURIComponent(m[2]) }) },
  { pattern: /^\/meetings\/([^/]+)\/?$/, view: meetingDetail, title: "Meeting", nav: "meetings", params: (m) => ({ id: decodeURIComponent(m[1]) }) },
  { pattern: /^\/tasks\/?$/, view: tasks, title: "Tasks", nav: "tasks" },
  { pattern: /^\/settings\/?$/, view: settings, title: "Settings", nav: "settings" },
];

let currentView = null;

/** Programmatic navigation. */
export function navigate(hash) {
  if (!hash.startsWith("#")) hash = "#" + hash;
  if (location.hash === hash) {
    handleRoute(); // re-render same route
  } else {
    location.hash = hash;
  }
}

function match() {
  const path = location.hash.replace(/^#/, "") || "/dashboard";
  for (const r of routes) {
    const m = path.match(r.pattern);
    if (m) return { route: r, params: r.params ? r.params(m) : {} };
  }
  return null;
}

export async function handleRoute() {
  const container = document.getElementById("view");
  const result = match();
  // Clean up the previous view (e.g. stop polling) before rendering the next.
  if (currentView && typeof currentView.cleanup === "function") {
    try { currentView.cleanup(); } catch { /* ignore */ }
  }

  // Scroll to top on navigation.
  container.parentElement?.scrollTo?.({ top: 0 });

  if (!result) {
    document.getElementById("page-title").textContent = "Not found";
    setActiveNav(null);
    container.innerHTML = `<div class="empty-state"><span class="emoji">🤷</span>Page not found.<br><a href="#/dashboard">Go to dashboard →</a></div>`;
    currentView = null;
    return;
  }

  const { route, params } = result;
  document.getElementById("page-title").textContent = route.title;
  setActiveNav(route.nav);
  currentView = route.view;
  try {
    await route.view.render(container, params);
  } catch (err) {
    container.innerHTML = `<div class="error-state">⚠️ ${err.message}</div>`;
  }
}

function setActiveNav(navKey) {
  document.querySelectorAll(".nav-item").forEach((a) => {
    a.classList.toggle("active", a.dataset.route === navKey);
  });
}
