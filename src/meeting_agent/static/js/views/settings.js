// settings.js — read-only system info & config view.
import { api } from "../api.js";
import { escapeHtml } from "../utils.js";

function configRow(key, value) {
  const display = value === true ? "✅ on" : value === false ? "⚪ off" : value;
  return `<div class="config-row"><span class="config-key">${escapeHtml(key)}</span><span class="config-val">${escapeHtml(String(display))}</span></div>`;
}

function providerRow(label, configured) {
  return `<div class="config-row"><span class="config-key">${escapeHtml(label)}</span>
    <span class="config-val ${configured ? "status-ok" : "status-no"}">${configured ? "● Configured" : "○ Not set"}</span></div>`;
}

export async function render(container) {
  container.innerHTML = `<div class="loading"><div class="spinner"></div> Loading settings…</div>`;
  try {
    const [health, info] = await Promise.all([api.health(), api.settingsInfo().catch(() => null)]);

    let configHtml = "";
    if (info) {
      configHtml = `
        <div class="config-row"><span class="config-key">Application</span><span class="config-val">${escapeHtml(info.app_name)}</span></div>
        ${configRow("Version", info.app_version)}
        ${configRow("Debug mode", info.debug)}
        ${configRow("OpenAI model", info.openai_model)}
        ${configRow("Whisper model", `${info.whisper_model_size} / ${info.whisper_device}`)}
        ${configRow("Email provider", info.email_provider)}
        ${configRow("From address", info.email_from_address)}
        ${configRow("Scheduler", info.scheduler_enabled ? `enabled` : "disabled")}
        ${configRow("Bot headless", info.bot_headless)}`;
    } else {
      configHtml = `<p class="muted">Configuration details unavailable.</p>`;
    }

    const providersHtml = info ? `
      ${providerRow("OpenAI API key", info.openai_configured)}
      ${providerRow("SendGrid API key", info.sendgrid_configured)}
      ${providerRow("SMTP credentials", info.smtp_configured)}` : "";

    container.innerHTML = `
      <div class="settings-grid">
        <div class="card">
          <div class="card-header"><span class="card-title">⚙️ Configuration</span></div>
          <div class="card-pad">${configHtml}</div>
        </div>
        <div class="flex" style="flex-direction:column; gap:18px;">
          <div class="card">
            <div class="card-header"><span class="card-title">🔐 Credentials</span></div>
            <div class="card-pad">
              ${providersHtml}
              <p class="muted" style="margin-top:14px; font-size:12.5px;">
                Settings are read from the <code>.env</code> file at startup. Edit <code>.env</code> and restart the server to change them.
              </p>
            </div>
          </div>
          <div class="card">
            <div class="card-header"><span class="card-title">💚 Service Health</span></div>
            <div class="card-pad">
              <div class="config-row"><span class="config-key">Status</span>
                <span class="config-val status-ok">${escapeHtml(health?.status || "unknown")}</span></div>
              <div class="config-row"><span class="config-key">Version</span>
                <span class="config-val">${escapeHtml(health?.version || "—")}</span></div>
            </div>
          </div>
        </div>
      </div>`;
  } catch (err) {
    container.innerHTML = `<div class="error-state">⚠️ Failed to load settings: ${escapeHtml(err.message)}</div>`;
  }
}
