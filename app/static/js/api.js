/**
 * Thin API client shared by every page.
 *
 * Holds the access token in sessionStorage, attaches the Authorization
 * header, turns API error bodies into readable messages, and handles the
 * role-based routing between the two application pages.
 */

const TOKEN_KEY = "fa.accessToken";

const LOGIN_PAGE = "/ui/";
const WORKSPACE_PAGE = "/ui/workspace.html";
const DEPARTMENT_PAGE = "/ui/department.html";

/** Where each role lands after signing in. */
const ROLE_HOME = {
  admin: WORKSPACE_PAGE,
  finance_officer: WORKSPACE_PAGE,
  department_head: DEPARTMENT_PAGE,
};

/* --- Session ------------------------------------------------------------- */

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function clearSession() {
  sessionStorage.removeItem(TOKEN_KEY);
}

function setToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

/** The page a role belongs on. Unknown roles go back to the login page. */
export function roleHome(role) {
  return ROLE_HOME[role] || LOGIN_PAGE;
}

export function goToRoleHome(role) {
  window.location.assign(roleHome(role));
}

export function signOut() {
  clearSession();
  window.location.assign(LOGIN_PAGE);
}

function onLoginPage() {
  const path = window.location.pathname;
  return path === LOGIN_PAGE || path === LOGIN_PAGE + "index.html";
}

/* --- Errors -------------------------------------------------------------- */

/**
 * Pull a human-readable message out of an error response.
 *
 * Handles the three shapes this API produces:
 *   {"detail": "text"}                      - HTTPException
 *   {"detail": {"rule": ..., "detail": ...}} - single-row validation failure
 *   {"detail": [{"msg": ..., ...}, ...]}     - request validation errors
 */
async function readErrorMessage(response) {
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  const detail = payload ? payload.detail : null;

  if (typeof detail === "string" && detail.trim() !== "") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item && typeof item.msg === "string" ? item.msg : null))
      .filter((message) => message !== null);
    if (messages.length > 0) {
      return messages.join("; ");
    }
  }

  if (detail && typeof detail === "object" && typeof detail.detail === "string") {
    return detail.detail;
  }

  return "The server could not complete that request (HTTP " + response.status + ").";
}

/* --- Core request -------------------------------------------------------- */

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = getToken();
  if (token) {
    headers.set("Authorization", "Bearer " + token);
  }

  const response = await fetch(path, { ...options, headers });

  if (response.status === 401) {
    clearSession();
    // Skip the redirect when the login page is probing a stale token,
    // otherwise the page would bounce to itself.
    if (!onLoginPage()) {
      window.location.assign(LOGIN_PAGE);
    }
    throw new Error("Your session has ended. Please sign in again.");
  }

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

/* --- Endpoints ----------------------------------------------------------- */

/**
 * Sign in. Posts form-encoded credentials to the OAuth2 token endpoint and
 * stores the token. A 401 here means bad credentials, not an expired
 * session, so it does not redirect.
 */
export async function login(username, password) {
  const body = new URLSearchParams();
  body.set("username", username);
  body.set("password", password);

  const response = await fetch("/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body,
  });

  if (response.status === 401) {
    throw new Error("Incorrect username or password.");
  }
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  const payload = await response.json();
  setToken(payload.access_token);
  return payload;
}

/** GET /auth/me - {username, role, department_id, department_name}. */
export function getMe() {
  return request("/auth/me");
}

export function apiGet(path) {
  return request(path);
}

export function apiPost(path, body) {
  const options = { method: "POST" };
  if (body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }
  return request(path, options);
}

/**
 * Multipart upload. The field name "file" matches the UploadFile parameter
 * in app/routers/ingest.py. Content-Type is left unset so the browser adds
 * the multipart boundary.
 */
export function apiUpload(path, file) {
  const form = new FormData();
  form.append("file", file, file.name);
  return request(path, { method: "POST", body: form });
}

/* --- Role guard ---------------------------------------------------------- */

/**
 * Guard a page by role.
 *
 * Returns the user object when the role is allowed. Returns null after
 * starting a redirect otherwise, so callers must stop on a null result:
 * navigation does not interrupt the script that triggered it.
 */
export async function requireRole(allowedRoles) {
  if (!getToken()) {
    window.location.assign(LOGIN_PAGE);
    return null;
  }

  let user;
  try {
    user = await getMe();
  } catch {
    // request() has already cleared the session and started the redirect.
    return null;
  }

  if (!allowedRoles.includes(user.role)) {
    goToRoleHome(user.role);
    return null;
  }

  return user;
}
