/**
 * FORAGRO Dashboard — session gate
 * ---------------------------------------------------------------------------
 * SECURITY NOTE — Missing authentication (most important fix in this project)
 * In the original single-page file, the dashboard (campaign stats, lead
 * names, phone numbers, discount codes) rendered on the SAME screen as the
 * public kiosk, with no login of any kind. Anyone standing at the kiosk in
 * the store — or anyone who loaded the file — could see every customer's
 * phone number and the store's campaign performance. That's a real privacy
 * problem (leaking customers' personal data) and a business one (competitors
 * can read your channel performance and ROI).
 *
 * Fix, in two parts:
 *   1. The dashboard is now a separate app (separate folder/origin/route)
 *      from the kiosk, so it is never displayed on the public terminal.
 *   2. This file gates the dashboard behind a real server-verified session.
 *      It does NOT store a token in localStorage/sessionStorage — those are
 *      readable by any script on the page, so a single XSS bug would hand
 *      over the session. Instead the backend should issue a session as an
 *      httpOnly, Secure, SameSite=Strict cookie on login; the browser sends
 *      it automatically and JavaScript never touches it directly.
 *
 * The actual access control decision MUST be enforced server-side on every
 * request (e.g. checking the session cookie before returning /api/metrics
 * or /api/leads). This client-side check only improves UX (redirecting
 * unauthenticated staff to the login screen); it is not, by itself, a
 * security boundary — a client can always be bypassed by calling the API
 * directly, which is exactly why the backend check is the one that matters.
 * ---------------------------------------------------------------------------
 */
async function requireSession() {
  try {
    await apiFetch("/api/session"); // 2xx => cookie is present and valid
  } catch {
    window.location.replace("login.html");
  }
}

requireSession();
