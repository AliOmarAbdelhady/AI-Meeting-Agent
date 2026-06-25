// modal.js — modal dialogs.
import { escapeHtml } from "../utils.js";

const root = () => document.getElementById("modal-root");

/**
 * Open a modal.
 * @param {object} opts
 * @param {string} opts.title
 * @param {string|HTMLElement} opts.body  - HTML string or a node
 * @param {Array} opts.actions - [{ label, variant, onClick(node), dismiss=true }]
 * @returns {HTMLElement} the modal body node (for querying forms inside)
 */
export function openModal({ title, body, actions = [] }) {
  closeModal();
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";

  const bodyHtml = typeof body === "string" ? body : '<div class="modal-body-host"></div>';
  overlay.innerHTML = `
    <div class="modal" role="dialog" aria-modal="true">
      <div class="modal-header">
        <div class="modal-title">${escapeHtml(title || "")}</div>
        <button class="modal-close" aria-label="Close">&times;</button>
      </div>
      <div class="modal-body">${bodyHtml}</div>
      <div class="modal-footer"></div>
    </div>`;

  const modal = overlay.querySelector(".modal");
  const footer = overlay.querySelector(".modal-footer");

  const close = () => overlay.remove();
  overlay.querySelector(".modal-close").addEventListener("click", close);
  overlay.addEventListener("mousedown", (e) => { if (e.target === overlay) close(); });
  document.addEventListener("keydown", function onKey(e) {
    if (e.key === "Escape") { close(); document.removeEventListener("keydown", onKey); }
  });

  for (const a of actions) {
    const btn = document.createElement("button");
    btn.className = `btn ${a.variant === "primary" ? "btn-primary" : a.variant === "danger" ? "btn-danger" : ""}`;
    btn.textContent = a.label;
    btn.addEventListener("click", () => {
      const dismiss = a.onClick ? a.onClick(modal) : true;
      if (dismiss !== false) close();
    });
    footer.appendChild(btn);
  }

  root().appendChild(overlay);

  // If body was a node, inject it.
  if (typeof body !== "string") {
    overlay.querySelector(".modal-body").innerHTML = "";
    overlay.querySelector(".modal-body").appendChild(body);
  }
  return modal;
}

export function closeModal() {
  root().innerHTML = "";
}

/** Promise-based confirmation dialog. Resolves true/false. */
export function confirmDialog(message, { title = "Confirm", okText = "Confirm", danger = false } = {}) {
  return new Promise((resolve) => {
    openModal({
      title,
      body: `<p style="margin:0">${escapeHtml(message)}</p>`,
      actions: [
        { label: "Cancel", onClick: () => resolve(false) },
        { label: okText, variant: danger ? "danger" : "primary", onClick: () => resolve(true) },
      ],
    });
  });
}
