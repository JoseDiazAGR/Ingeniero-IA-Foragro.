/**
 * FORAGRO — Shared utilities
 * ---------------------------------------------------------------------------
 * SECURITY NOTE — Cross-Site Scripting (XSS)
 * The original code built HTML strings with template literals and dropped
 * them straight into `innerHTML`, e.g.:
 *
 *   extraContent.innerHTML = `<div>${leadData.telefono}</div>`;
 *
 * `leadData.telefono` and `leadData.manzanas` come from a free-text <input>
 * the customer types into. Someone at the kiosk could type
 * `<img src=x onerror=alert(document.cookie)>` as their "phone number" and
 * have it executed as real HTML/JS as soon as the coupon card renders —
 * a classic stored/reflected XSS. The same problem existed in the dashboard
 * when rendering lead rows and campaign labels.
 *
 * Fix: every dynamic value that is concatenated into an HTML string now goes
 * through `escapeHTML()` first. As a rule, never interpolate unescaped user
 * input (or backend data you don't fully trust) into `innerHTML`.
 * ---------------------------------------------------------------------------
 */

/** Escapes text so it can be safely inserted into innerHTML. */
function escapeHTML(value) {
  const str = value === undefined || value === null ? "" : String(value);
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Loosely validates a Honduran-style phone number (accepts spaces/dashes,
 * optional +504 prefix, 8 local digits). This is a UX guard, not a security
 * boundary — the backend must validate/normalize again server-side.
 */
function isValidPhone(value) {
  const digits = String(value || "").replace(/[^\d]/g, "");
  // +504 (country code, optional) + 8-digit local number
  return /^(504)?\d{8}$/.test(digits);
}

/** Validates the "manzanas" (land area) field as a positive number. */
function isValidManzanas(value) {
  const n = Number(String(value || "").replace(",", "."));
  return Number.isFinite(n) && n > 0 && n <= 100000;
}

/**
 * fetch() wrapper that adds a timeout (so a hung backend can't freeze the
 * UI), rejects non-2xx responses instead of silently treating them as
 * success, and centralizes error logging so failures aren't swallowed
 * invisibly (the original code used bare `.catch(() => {})`, which hides
 * real outages/attacks from anyone debugging the system).
 */
async function apiFetch(path, options = {}) {
  const base = window.FORAGRO_CONFIG?.API_BASE || "";
  const timeoutMs = window.FORAGRO_CONFIG?.FETCH_TIMEOUT_MS || 8000;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(base + path, {
      credentials: "include", // send the session cookie set by the backend, if any
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`Request to ${path} failed with status ${response.status}`);
    }

    const contentType = response.headers.get("content-type") || "";
    return contentType.includes("application/json") ? response.json() : null;
  } finally {
    clearTimeout(timer);
  }
}

/** Shows a small toast. `isError` swaps in the red/error styling. */
function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 3000);
}
