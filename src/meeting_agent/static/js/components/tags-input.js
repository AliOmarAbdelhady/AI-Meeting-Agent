// tags-input.js — email chip input. Reused for participants & recipients.
import { escapeHtml, isValidEmail } from "../utils.js";

/**
 * Build a tags input element.
 * @param {string[]} initial
 * @param {object} opts { placeholder, validate }
 * @returns {{ el: HTMLElement, getValue: () => string[], setValues: (string[]) => void }}
 */
export function createTagsInput(initial = [], { placeholder = "Add and press Enter…", validate = isValidEmail } = {}) {
  const wrap = document.createElement("div");
  wrap.className = "tags-input";
  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = placeholder;

  let tags = [...initial];

  const render = () => {
    // Remove existing chips, keep input
    [...wrap.querySelectorAll(".tag-chip")].forEach((c) => c.remove());
    for (const tag of tags) {
      const chip = document.createElement("span");
      const valid = validate(tag);
      chip.className = `tag-chip${valid ? "" : " invalid"}`;
      chip.innerHTML = `<span>${escapeHtml(tag)}</span><button type="button" aria-label="remove">&times;</button>`;
      chip.querySelector("button").addEventListener("click", () => {
        tags = tags.filter((t) => t !== tag);
        render();
      });
      wrap.insertBefore(chip, input);
    }
  };

  const addFromInput = () => {
    const raw = input.value.trim();
    if (!raw) return;
    // Support comma / whitespace separated paste.
    const parts = raw.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);
    for (const p of parts) {
      if (!tags.includes(p)) tags.push(p);
    }
    input.value = "";
    render();
  };

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addFromInput();
    } else if (e.key === "Backspace" && !input.value && tags.length) {
      tags.pop();
      render();
    }
  });
  input.addEventListener("blur", addFromInput);
  input.addEventListener("paste", (e) => {
    e.preventDefault();
    input.value = (e.clipboardData || window.clipboardData).getData("text");
    addFromInput();
  });

  wrap.addEventListener("click", () => input.focus());
  input.addEventListener("focus", () => wrap.classList.add("focus"));
  input.addEventListener("blur", () => wrap.classList.remove("focus"));

  wrap.appendChild(input);
  render();

  return {
    el: wrap,
    getValue: () => [...tags],
    setValues: (vals) => { tags = [...(vals || [])]; render(); },
  };
}
