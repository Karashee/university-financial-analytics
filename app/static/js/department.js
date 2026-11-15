/**
 * Department head view: read-only flagged transactions and expenditure
 * forecast for the signed-in user's own department.
 *
 * No client-side department filtering is applied anywhere in this file -
 * the server already scopes both GET /anomaly/results and GET /forecasts
 * by department_id via get_dept_filter(). That is the point of the page.
 */

import { apiGet, requireRole } from "./api.js";
import { renderTopBar } from "./layout.js";

const heading = document.querySelector("#department-heading");

const flaggedBody = document.querySelector("#flagged-body");
const flaggedEmpty = document.querySelector("#flagged-empty");
const flaggedEmptyMessage = flaggedEmpty.textContent;

const forecastBody = document.querySelector("#forecast-body");
const forecastEmpty = document.querySelector("#forecast-empty");
const forecastEmptyMessage = forecastEmpty.textContent;

/* --- Small helpers --------------------------------------------------------
   Each page script in this app is self-contained, matching login.js and
   workspace.js: no shared formatting module exists, so these are repeated
   here in the same style rather than introduced as a new dependency. */

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

function show(node) {
  node.hidden = false;
}

function hide(node) {
  node.hidden = true;
}

/** Money as `Ksh 1,404,879`, per the design spec: no decimals. */
function formatMoney(value) {
  return "Ksh " + Math.round(Number(value)).toLocaleString("en-US");
}

/**
 * A transaction_date string ("2023-11-11") as "11 Nov 2023".
 * Built from the parts directly rather than through Date parsing, so a
 * viewer west of UTC can never see the date shift back by a day.
 */
function formatTransactionDate(isoDate) {
  const [year, month, day] = isoDate.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

/** fiscal_year/fiscal_month as "Jan 2026". */
function formatFiscalMonth(fiscalYear, fiscalMonth) {
  const date = new Date(fiscalYear, fiscalMonth - 1, 1);
  return date.toLocaleDateString("en-GB", { month: "short", year: "numeric" });
}

/* --- Flagged transactions -------------------------------------------------
   Lower anomaly_score means more anomalous (it is the Isolation Forest's
   decision_function output - see app/ml/isolation_forest.py), so "most
   anomalous first" is an ascending sort. */

function renderFlagged(rows) {
  flaggedBody.replaceChildren();

  if (rows.length === 0) {
    flaggedEmpty.textContent = flaggedEmptyMessage;
    show(flaggedEmpty);
    return;
  }
  hide(flaggedEmpty);

  const sorted = rows.slice().sort((a, b) => a.anomaly_score - b.anomaly_score);

  sorted.forEach((row) => {
    const tr = element("tr");
    tr.appendChild(element("td", null, formatTransactionDate(row.transaction_date)));
    tr.appendChild(element("td", null, row.transaction_id));
    tr.appendChild(element("td", null, row.expenditure_category));
    tr.appendChild(element("td", "td--numeric", formatMoney(row.transaction_amount)));
    tr.appendChild(element("td", "td--numeric", Number(row.anomaly_score).toFixed(3)));
    tr.appendChild(element("td", null, row.explanation));
    flaggedBody.appendChild(tr);
  });
}

async function loadFlagged() {
  try {
    const rows = await apiGet("/anomaly/results?is_anomaly_predicted=true");
    renderFlagged(rows);
  } catch (error) {
    flaggedBody.replaceChildren();
    flaggedEmpty.textContent = error.message;
    show(flaggedEmpty);
  }
}

/* --- Expenditure forecast -------------------------------------------------- */

function renderForecast(rows) {
  forecastBody.replaceChildren();

  if (rows.length === 0) {
    forecastEmpty.textContent = forecastEmptyMessage;
    show(forecastEmpty);
    return;
  }
  hide(forecastEmpty);

  const sorted = rows.slice().sort((a, b) =>
    a.fiscal_year - b.fiscal_year || a.fiscal_month - b.fiscal_month
  );

  sorted.forEach((row) => {
    const tr = element("tr");
    tr.appendChild(element("td", null, formatFiscalMonth(row.fiscal_year, row.fiscal_month)));
    tr.appendChild(element("td", "td--numeric", formatMoney(row.predicted_expenditure)));
    forecastBody.appendChild(tr);
  });
}

async function loadForecast() {
  try {
    const rows = await apiGet("/forecasts");
    renderForecast(rows);
  } catch (error) {
    forecastBody.replaceChildren();
    forecastEmpty.textContent = error.message;
    show(forecastEmpty);
  }
}

/* --- Boot ------------------------------------------------------------------ */

const user = await requireRole(["department_head"]);
if (user) {
  renderTopBar(user);
  if (user.department_name) {
    heading.textContent = user.department_name;
  }

  await Promise.all([loadFlagged(), loadForecast()]);
}
