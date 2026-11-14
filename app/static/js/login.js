/**
 * Login page behaviour.
 *
 * Nothing sensitive is ever logged: the password is read straight from the
 * form into the request body and never stored or printed.
 */

import { getMe, getToken, goToRoleHome, login } from "./api.js";

const form = document.querySelector("#login-form");
const usernameInput = document.querySelector("#username");
const passwordInput = document.querySelector("#password");
const submitButton = document.querySelector("#sign-in");
const banner = document.querySelector("#login-error");
const bannerText = document.querySelector("#login-error-text");

function showError(message) {
  bannerText.textContent = message;
  banner.hidden = false;
}

function clearError() {
  bannerText.textContent = "";
  banner.hidden = true;
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.classList.toggle("is-loading", isLoading);
  submitButton.setAttribute("aria-busy", isLoading ? "true" : "false");
}

/**
 * If this tab already holds a valid token, go straight to the right page.
 * A stale token is cleared by api.js and the form is shown instead.
 */
async function skipIfSignedIn() {
  if (!getToken()) {
    return;
  }
  try {
    const user = await getMe();
    goToRoleHome(user.role);
  } catch {
    // Stale or rejected token: stay on the login form.
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();

  const username = usernameInput.value.trim();
  const password = passwordInput.value;

  if (!username || !password) {
    showError("Enter both a username and a password.");
    return;
  }

  setLoading(true);
  try {
    await login(username, password);
    const user = await getMe();
    goToRoleHome(user.role);
  } catch (error) {
    showError(error.message);
    setLoading(false);
    passwordInput.value = "";
    passwordInput.focus();
  }
});

skipIfSignedIn();
