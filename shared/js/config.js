/**
 * FORAGRO — Runtime configuration
 * ---------------------------------------------------------------------------
 * SECURITY NOTE
 * The original file hardcoded `http://localhost:8000` directly inside the
 * business-logic script. That has two problems:
 *   1. Plaintext HTTP would send lead data (names, phone numbers) unencrypted.
 *   2. A hardcoded value forces a code edit (and a new deploy) for every
 *      environment, which invites someone to accidentally ship a dev/staging
 *      URL to production, or vice versa.
 *
 * Fix: every environment gets this one file swapped at deploy time (or the
 * values are injected by your server/build step). The rest of the app never
 * references a URL literal directly. Always use HTTPS in staging/production.
 * ---------------------------------------------------------------------------
 */
window.FORAGRO_CONFIG = Object.freeze({
  // Si se ejecuta con http.server en el puerto 8080 apunta a localhost:8000.
  // Si se ejecuta servido por FastAPI o desplegado en la nube (Render, Railway), usa el mismo origen actual.
  API_BASE: window.location.origin.includes(":8080")
    ? "http://localhost:8000"
    : (window.location.origin.startsWith("http") ? window.location.origin : "http://localhost:8000"),

  // Toggle client features without touching business logic.
  FEATURES: Object.freeze({
    VOICE_INPUT: true,
    VOICE_OUTPUT: true,
  }),

  // Abort any API call that hangs longer than this (ms). Prevents a slow/dead
  // backend from freezing the kiosk UI indefinitely.
  FETCH_TIMEOUT_MS: 8000,
});
