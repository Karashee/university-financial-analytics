/**
 * Shared page furniture: the top bar.
 *
 * Everything is built with createElement and textContent - API values are
 * never written into the page as HTML.
 */

import { signOut } from "./api.js";

/** Role name from the API -> label shown in the top bar. */
const ROLE_LABELS = {
  admin: "Administrator",
  finance_officer: "Finance Officer",
  department_head: "Department Head",
};

export function roleLabel(role) {
  return ROLE_LABELS[role] || role;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text !== undefined) {
    node.textContent = text;
  }
  return node;
}

/**
 * Render the top bar into a mount point.
 *
 * @param {{username: string, role: string}} user - from GET /auth/me
 * @param {string} mountSelector - defaults to "#top-bar"
 */
export function renderTopBar(user, mountSelector = "#top-bar") {
  const mount = document.querySelector(mountSelector);
  if (!mount) {
    return;
  }

  const header = element("header", "topbar");
  const inner = element("div", "topbar__inner");

  const brand = element("div", "topbar__brand");
  const logo = element("span", "logo-mark", "FA");
  logo.setAttribute("aria-hidden", "true");
  brand.appendChild(logo);
  brand.appendChild(element("span", "topbar__title", "Financial Analytics"));

  const account = element("div", "topbar__user");
  account.appendChild(element("span", "topbar__username", user.username));
  account.appendChild(element("span", "pill pill--role", roleLabel(user.role)));

  const signOutButton = element("button", "btn-text", "Sign out");
  signOutButton.type = "button";
  signOutButton.addEventListener("click", signOut);
  account.appendChild(signOutButton);

  inner.appendChild(brand);
  inner.appendChild(account);
  header.appendChild(inner);

  mount.replaceChildren(header);
}
