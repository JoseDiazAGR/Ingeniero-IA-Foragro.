/**
 * FORAGRO Dashboard — login form
 * ---------------------------------------------------------------------------
 * Posts credentials over HTTPS to the backend, which should:
 *   - Compare against a hashed password (bcrypt/argon2), never plaintext.
 *   - Rate-limit / lock out after repeated failures (brute-force defense).
 *   - Set the session as an httpOnly, Secure, SameSite=Strict cookie.
 *   - Return a generic "usuario o contraseña incorrectos" on any failure —
 *     never reveal whether the username or the password was wrong.
 * This file intentionally never stores the password or a token client-side.
 * ---------------------------------------------------------------------------
 */
(function () {
  "use strict";

  const form = document.getElementById("loginForm");
  const errorEl = document.getElementById("loginError");
  const submitBtn = document.getElementById("loginSubmit");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorEl.textContent = "";
    submitBtn.disabled = true;

    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;

    try {
      await apiFetch("/api/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      window.location.replace("index.html");
    } catch (err) {
      console.error("Login failed:", err);
      errorEl.textContent = "Usuario o contraseña incorrectos.";
    } finally {
      submitBtn.disabled = false;
    }
  });
})();
