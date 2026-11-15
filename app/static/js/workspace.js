/**
 * Workspace, step 1: choose a CSV, preview it, check its columns, and send
 * it to the ingestion endpoint.
 *
 * Steps 2 and 3 (run analysis, results) are filled in by the next chunk.
 * Every value that comes back from the API is written with textContent.
 */

import { apiGet, apiPost, apiUpload, requireRole } from "./api.js";
import { readCsvPreview, PREVIEW_ROW_COUNT } from "./csv-preview.js";
import { renderTopBar } from "./layout.js";

/**
 * The 18 columns the ingestion pipeline expects, copied exactly from the
 * header row of data/synthetic_university_financial_data_final.csv.
 */
const REQUIRED_COLUMNS = [
  "Transaction_ID",
  "Department_ID",
  "Department_Name",
  "Department_Type",
  "Fiscal_Year",
  "Fiscal_Month",
  "Transaction_Date",
  "Budget_Allocation",
  "Monthly_Expenditure",
  "Transaction_Amount",
  "Expenditure_Category",
  "Vendor_Category",
  "Budget_Utilization_Percentage",
  "Expenditure_Variance",
  "Historical_Average_Expenditure",
  "Expenditure_Growth_Rate",
  "Is_Anomaly",
  "Anomaly_Type",
];

/** Validation rule codes from scripts/validate_csv.py, in plain words. */
const RULE_LABELS = {
  RULE_1_UTILIZATION: "Utilisation outside 0\u2013100%",
  RULE_2_AMOUNT: "Amount not positive",
  RULE_3_VARIANCE: "Variance arithmetic mismatch",
  RULE_4_NULL: "Required field missing",
  RULE_5_DATE: "Date outside fiscal period",
};

const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;

const dropzone = document.querySelector("#dropzone");
const fileInput = document.querySelector("#file-input");
const fileError = document.querySelector("#file-error");
const fileErrorText = document.querySelector("#file-error-text");
const fileChip = document.querySelector("#file-chip");
const fileChipName = document.querySelector("#file-chip-name");
const fileChipSize = document.querySelector("#file-chip-size");
const fileRemove = document.querySelector("#file-remove");

const previewBlock = document.querySelector("#preview-block");
const previewHead = document.querySelector("#preview-head");
const previewBody = document.querySelector("#preview-body");

const columnsBlock = document.querySelector("#columns-block");
const columnGrid = document.querySelector("#column-grid");
const columnsWarning = document.querySelector("#columns-warning");
const columnsWarningText = document.querySelector("#columns-warning-text");

const uploadButton = document.querySelector("#upload-button");
const uploadError = document.querySelector("#upload-error");
const uploadErrorText = document.querySelector("#upload-error-text");
const uploadResult = document.querySelector("#upload-result");

const statInserted = document.querySelector("#stat-inserted");
const statSkipped = document.querySelector("#stat-skipped");
const statRejected = document.querySelector("#stat-rejected");
const statRejectedTile = document.querySelector("#stat-rejected-tile");
const allDuplicatesBanner = document.querySelector("#all-duplicates-banner");
const rejectedBlock = document.querySelector("#rejected-block");
const rejectedBody = document.querySelector("#rejected-body");

const sectionAnalysis = document.querySelector("#section-analysis");
const analysisLockedNote = document.querySelector("#analysis-locked-note");
const analysisControls = document.querySelector("#analysis-controls");
const forecastHorizon = document.querySelector("#forecast-horizon");
const runButton = document.querySelector("#run-button");
const retryButton = document.querySelector("#retry-button");
const stepper = document.querySelector("#stepper");

const sectionResults = document.querySelector("#section-results");
const resultScored = document.querySelector("#result-scored");
const resultFlagged = document.querySelector("#result-flagged");
const resultFlaggedMeta = document.querySelector("#result-flagged-meta");
const resultForecasts = document.querySelector("#result-forecasts");
const resultForecastsMeta = document.querySelector("#result-forecasts-meta");
const resultDuration = document.querySelector("#result-duration");
const activityList = document.querySelector("#activity-list");
const activityMessage = document.querySelector("#activity-message");
const activityRefresh = document.querySelector("#activity-refresh");

/** The file waiting to be uploaded, and whether its columns check out. */
let selectedFile = null;
let columnsComplete = false;

/** Per-step {result, seconds} for the current run, and where a failure stopped. */
let stepOutcomes = [];
let failedStepIndex = null;

/* --- Small helpers ------------------------------------------------------- */

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

/** Counts get thousands separators, per the design spec. */
function formatCount(value) {
  return Number(value).toLocaleString("en-US");
}

function formatFileSize(bytes) {
  if (bytes < 1024) {
    return bytes + " B";
  }
  const kilobytes = bytes / 1024;
  if (kilobytes < 1024) {
    return kilobytes.toFixed(1) + " KB";
  }
  return (kilobytes / 1024).toFixed(1) + " MB";
}

/** Money as `Ksh 1,404,879`, per the design spec: no decimals. */
function formatMoney(value) {
  return "Ksh " + Math.round(Number(value)).toLocaleString("en-US");
}

/** Percentages to one decimal. */
function formatPercent(value) {
  return Number(value).toFixed(1) + "%";
}

/** Elapsed time, e.g. "0.8 s". */
function formatSeconds(seconds) {
  return seconds.toFixed(1) + " s";
}

/** A log timestamp as HH:MM:SS in the viewer's own timezone. */
function formatClockTime(isoTimestamp) {
  const when = new Date(isoTimestamp);
  if (Number.isNaN(when.getTime())) {
    return "--:--:--";
  }
  return when.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function ruleLabel(rule) {
  return RULE_LABELS[rule] || rule;
}

function showFileError(message) {
  fileErrorText.textContent = message;
  show(fileError);
}

function clearFileError() {
  fileErrorText.textContent = "";
  hide(fileError);
}

function showUploadError(message) {
  uploadErrorText.textContent = message;
  show(uploadError);
}

function clearUploadError() {
  uploadErrorText.textContent = "";
  hide(uploadError);
}

function setUploading(isUploading) {
  uploadButton.disabled = isUploading || selectedFile === null || !columnsComplete;
  uploadButton.classList.toggle("is-loading", isUploading);
  uploadButton.setAttribute("aria-busy", isUploading ? "true" : "false");
}

function refreshUploadButton() {
  uploadButton.disabled = selectedFile === null || !columnsComplete;
}

/* --- Preview and column check ------------------------------------------- */

function renderPreview(columns, rows) {
  previewHead.replaceChildren();
  previewBody.replaceChildren();

  columns.forEach((name) => {
    previewHead.appendChild(element("th", null, name));
  });

  rows.forEach((row) => {
    const tr = element("tr");
    // Pad short rows so the preview stays aligned with the header.
    for (let index = 0; index < columns.length; index += 1) {
      tr.appendChild(element("td", null, row[index] !== undefined ? row[index] : ""));
    }
    previewBody.appendChild(tr);
  });

  show(previewBlock);
}

function columnCheckRow(name, state) {
  const classes = {
    present: "column-check column-check--present",
    missing: "column-check column-check--missing",
    ignored: "column-check column-check--ignored",
  };
  const icons = { present: "\u2713", missing: "\u2717", ignored: "\u2022" };

  const row = element("div", classes[state]);
  const icon = element("span", "column-check__icon", icons[state]);
  icon.setAttribute("aria-hidden", "true");
  row.appendChild(icon);
  row.appendChild(element("span", "column-check__name", name));

  // Text alongside the icon, so colour is never the only signal.
  if (state === "missing") {
    row.appendChild(element("span", "column-check__tag", "missing"));
  } else if (state === "ignored") {
    row.appendChild(element("span", "column-check__tag", "ignored"));
  }
  return row;
}

function renderColumnCheck(columns) {
  columnGrid.replaceChildren();

  const present = new Set(columns);
  const missing = REQUIRED_COLUMNS.filter((name) => !present.has(name));
  const extras = columns.filter((name) => name !== "" && !REQUIRED_COLUMNS.includes(name));

  REQUIRED_COLUMNS.forEach((name) => {
    columnGrid.appendChild(columnCheckRow(name, present.has(name) ? "present" : "missing"));
  });
  extras.forEach((name) => {
    columnGrid.appendChild(columnCheckRow(name, "ignored"));
  });

  show(columnsBlock);

  columnsComplete = missing.length === 0;
  if (columnsComplete) {
    hide(columnsWarning);
    return;
  }

  const noun = missing.length === 1 ? "column" : "columns";
  columnsWarningText.textContent =
    missing.length + " required " + noun + " missing (" + missing.join(", ") +
    "). Upload is disabled until the file has every required column.";
  show(columnsWarning);
}

/* --- File selection ------------------------------------------------------ */

function clearSelection() {
  selectedFile = null;
  columnsComplete = false;
  fileInput.value = "";

  hide(fileChip);
  hide(previewBlock);
  hide(columnsBlock);
  hide(columnsWarning);
  hide(uploadResult);
  clearUploadError();
  previewHead.replaceChildren();
  previewBody.replaceChildren();
  columnGrid.replaceChildren();
  refreshUploadButton();
}

async function selectFile(file) {
  clearFileError();
  hide(uploadResult);
  clearUploadError();

  if (!file.name.toLowerCase().endsWith(".csv")) {
    clearSelection();
    showFileError("That file is not a CSV. Choose a file ending in .csv.");
    return;
  }

  if (file.size > MAX_UPLOAD_BYTES) {
    clearSelection();
    showFileError("That file is " + formatFileSize(file.size) + ". The limit is 20 MB.");
    return;
  }

  selectedFile = file;
  fileChipName.textContent = file.name;
  fileChipSize.textContent = formatFileSize(file.size);
  show(fileChip);

  try {
    const preview = await readCsvPreview(selectedFile, PREVIEW_ROW_COUNT);
    if (preview.columns.length === 0) {
      clearSelection();
      showFileError("That file appears to be empty.");
      return;
    }
    renderPreview(preview.columns, preview.rows);
    renderColumnCheck(preview.columns);
  } catch {
    clearSelection();
    showFileError("That file could not be read. Check that it is a plain CSV file.");
    return;
  }

  // Clear the input's value so picking the same file again still fires a
  // change event. selectedFile already holds its own reference to the File.
  fileInput.value = "";
  refreshUploadButton();
}

/* --- Upload and results -------------------------------------------------- */

function renderRejectedRows(rejectedRows) {
  rejectedBody.replaceChildren();

  if (rejectedRows.length === 0) {
    hide(rejectedBlock);
    return;
  }

  rejectedRows.forEach((entry) => {
    const tr = element("tr", "is-rejected");
    tr.appendChild(element("td", null, String(entry.row_index)));

    const transactionId =
      entry.transaction_id === null || entry.transaction_id === undefined
        ? "\u2014"
        : String(entry.transaction_id);
    tr.appendChild(element("td", null, transactionId));

    const ruleCell = element("td");
    ruleCell.appendChild(element("span", "pill pill--danger", ruleLabel(entry.rule)));
    tr.appendChild(ruleCell);

    tr.appendChild(element("td", null, entry.detail));
    rejectedBody.appendChild(tr);
  });

  show(rejectedBlock);
}

function unlockAnalysisSection() {
  sectionAnalysis.classList.remove("section-card--locked");
  hide(analysisLockedNote);
  show(analysisControls);
  sectionAnalysis.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderUploadResult(result) {
  const inserted = result.inserted_rows;
  const skipped = result.skipped_rows;
  const rejectedRows = result.rejected_rows || [];

  statInserted.textContent = formatCount(inserted);
  statSkipped.textContent = formatCount(skipped);
  statRejected.textContent = formatCount(rejectedRows.length);
  statRejectedTile.classList.toggle("stat-tile--danger", rejectedRows.length > 0);

  if (inserted === 0 && skipped > 0) {
    show(allDuplicatesBanner);
  } else {
    hide(allDuplicatesBanner);
  }

  renderRejectedRows(rejectedRows);
  show(uploadResult);

  if (inserted > 0 || skipped > 0) {
    unlockAnalysisSection();
  }
}

async function uploadSelectedFile() {
  if (selectedFile === null || !columnsComplete) {
    return;
  }

  clearUploadError();
  hide(uploadResult);
  setUploading(true);

  try {
    const result = await apiUpload("/ingest/csv", selectedFile);
    renderUploadResult(result);
  } catch (error) {
    showUploadError(error.message);
  } finally {
    setUploading(false);
  }
}

/* --- Analysis pipeline --------------------------------------------------- */

/**
 * The four stages, run in this order. Anomaly detection must precede the
 * forecast so flagged records are excluded from forecast training.
 * Response keys come from app/services: rows_written, total_scored,
 * flagged_count, total_forecasts, mae_context, n_months_ahead.
 */
const PIPELINE_STEPS = [
  {
    name: "Budget utilisation",
    run: () => apiPost("/analytics/compute/budget-utilization"),
    describe: (result) => formatCount(result.rows_written) + " rows written",
  },
  {
    name: "Trend summaries",
    run: () => apiPost("/reporting/compute/trend-summaries"),
    describe: (result) => formatCount(result.rows_written) + " rows written",
  },
  {
    name: "Anomaly detection",
    run: () => apiPost("/anomaly/detect"),
    describe: (result) =>
      formatCount(result.total_scored) + " scored \u00b7 " +
      formatCount(result.flagged_count) + " flagged",
  },
  {
    name: "Expenditure forecast",
    run: () => apiPost("/forecasts/run?n_months=" + selectedHorizon()),
    // "training MAE": the error on the training data, not a hold-out figure.
    describe: (result) =>
      formatCount(result.total_forecasts) + " forecasts \u00b7 training MAE " +
      formatMoney(result.mae_context),
  },
];

const STEP_GLYPHS = { pending: "\u25cb", done: "\u2713", failed: "\u2717" };

function selectedHorizon() {
  return Number(forecastHorizon.value);
}

function stepRow(index) {
  return stepper.children[index];
}

/** Paint one stepper row. A spinner replaces the glyph while running. */
function setStepState(index, state, resultText, seconds) {
  const row = stepRow(index);
  row.className = "stepper__row stepper__row--" + state;

  const status = row.querySelector(".stepper__status");
  if (state === "running") {
    const spinner = element("span", "spinner");
    spinner.setAttribute("aria-hidden", "true");
    status.replaceChildren(spinner);
  } else {
    const glyph = element("span", "stepper__glyph", STEP_GLYPHS[state] || "");
    glyph.setAttribute("aria-hidden", "true");
    status.replaceChildren(glyph);
  }

  row.querySelector(".stepper__result").textContent = resultText || "";
  row.querySelector(".stepper__time").textContent =
    seconds === undefined ? "" : formatSeconds(seconds);
}

function renderStepper() {
  stepper.replaceChildren();
  PIPELINE_STEPS.forEach((step) => {
    const row = element("li", "stepper__row stepper__row--pending");

    const status = element("span", "stepper__status");
    const glyph = element("span", "stepper__glyph", STEP_GLYPHS.pending);
    glyph.setAttribute("aria-hidden", "true");
    status.appendChild(glyph);

    row.appendChild(status);
    row.appendChild(element("span", "stepper__name", step.name));
    row.appendChild(element("span", "stepper__result"));
    row.appendChild(element("span", "stepper__time"));
    stepper.appendChild(row);
  });
}

function setRunning(isRunning) {
  runButton.disabled = isRunning;
  runButton.classList.toggle("is-loading", isRunning);
  runButton.setAttribute("aria-busy", isRunning ? "true" : "false");
  retryButton.disabled = isRunning;
  retryButton.classList.toggle("is-loading", isRunning);
  forecastHorizon.disabled = isRunning;
}

/**
 * Run the stages from startIndex onwards, stopping at the first failure.
 * Steps before startIndex keep the results from the earlier attempt, so a
 * retry does not repeat work that already succeeded.
 */
async function runPipeline(startIndex = 0) {
  if (startIndex === 0) {
    stepOutcomes = [];
    renderStepper();
    hide(sectionResults);
  } else {
    for (let index = startIndex; index < PIPELINE_STEPS.length; index += 1) {
      setStepState(index, "pending", "", undefined);
    }
  }

  failedStepIndex = null;
  hide(retryButton);
  setRunning(true);

  for (let index = startIndex; index < PIPELINE_STEPS.length; index += 1) {
    const step = PIPELINE_STEPS[index];
    setStepState(index, "running", "Running\u2026", undefined);

    const startedAt = performance.now();
    try {
      const result = await step.run();
      const seconds = (performance.now() - startedAt) / 1000;
      stepOutcomes[index] = { result: result, seconds: seconds };
      setStepState(index, "done", step.describe(result), seconds);
    } catch (error) {
      const seconds = (performance.now() - startedAt) / 1000;
      setStepState(index, "failed", error.message, seconds);
      failedStepIndex = index;
      show(retryButton);
      setRunning(false);
      return;
    }
  }

  setRunning(false);
  renderResults();
}

/* --- Results ------------------------------------------------------------- */

function renderResults() {
  const anomaly = stepOutcomes[2].result;
  const forecast = stepOutcomes[3].result;

  const totalScored = anomaly.total_scored;
  const flagged = anomaly.flagged_count;
  const totalForecasts = forecast.total_forecasts;
  const months = forecast.n_months_ahead;

  resultScored.textContent = formatCount(totalScored);

  resultFlagged.textContent = formatCount(flagged);
  resultFlaggedMeta.textContent =
    totalScored > 0
      ? formatPercent((flagged / totalScored) * 100) + " of transactions"
      : "no transactions scored";

  resultForecasts.textContent = formatCount(totalForecasts);
  if (months > 0) {
    const departments = totalForecasts / months;
    resultForecastsMeta.textContent =
      formatCount(months) + " months \u00d7 " + formatCount(departments) + " departments";
  } else {
    resultForecastsMeta.textContent = "";
  }

  const totalSeconds = stepOutcomes.reduce(
    (sum, outcome) => sum + (outcome ? outcome.seconds : 0),
    0
  );
  resultDuration.textContent = formatSeconds(totalSeconds);

  show(sectionResults);
  loadActivity();
  sectionResults.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* --- Recent system activity ---------------------------------------------- */

const LEVEL_PILL_CLASS = {
  INFO: "pill pill--neutral",
  WARNING: "pill pill--warning",
  ERROR: "pill pill--danger",
  CRITICAL: "pill pill--danger",
};

function activityRow(entry) {
  const row = element("div", "activity-row");
  row.appendChild(element("span", "activity-row__time", formatClockTime(entry.logged_at)));

  const pill = element(
    "span",
    LEVEL_PILL_CLASS[entry.level] || "pill pill--neutral",
    entry.level
  );
  row.appendChild(pill);

  const message = element("span", "activity-row__message", entry.message);
  message.title = entry.message;
  row.appendChild(message);
  return row;
}

/**
 * Load the newest log entries. A failure here is reported quietly: the
 * pipeline has already succeeded and the page must not break over it.
 */
async function loadActivity() {
  hide(activityMessage);
  try {
    const entries = await apiGet("/logs?limit=8");
    activityList.replaceChildren();

    if (entries.length === 0) {
      activityMessage.textContent = "No activity recorded yet.";
      show(activityMessage);
      return;
    }

    entries.forEach((entry) => activityList.appendChild(activityRow(entry)));
  } catch {
    activityList.replaceChildren();
    activityMessage.textContent = "Recent activity is unavailable just now.";
    show(activityMessage);
  }
}

/* --- Events -------------------------------------------------------------- */

dropzone.addEventListener("click", () => fileInput.click());

dropzone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    fileInput.click();
  }
});

["dragenter", "dragover"].forEach((name) => {
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.add("dropzone--active");
  });
});

["dragleave", "dragend"].forEach((name) => {
  dropzone.addEventListener(name, () => {
    dropzone.classList.remove("dropzone--active");
  });
});

dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("dropzone--active");
  const dropped = event.dataTransfer ? event.dataTransfer.files : null;
  if (dropped && dropped.length > 0) {
    selectFile(dropped[0]);
  }
});

fileInput.addEventListener("change", () => {
  if (fileInput.files && fileInput.files.length > 0) {
    selectFile(fileInput.files[0]);
  }
});

fileRemove.addEventListener("click", () => {
  clearSelection();
  clearFileError();
});

uploadButton.addEventListener("click", uploadSelectedFile);

runButton.addEventListener("click", () => runPipeline(0));

retryButton.addEventListener("click", () => {
  if (failedStepIndex !== null) {
    runPipeline(failedStepIndex);
  }
});

activityRefresh.addEventListener("click", loadActivity);

// A file dropped outside the zone would otherwise navigate away from the app.
["dragover", "drop"].forEach((name) => {
  window.addEventListener(name, (event) => {
    if (!dropzone.contains(event.target)) {
      event.preventDefault();
    }
  });
});

/* --- Boot ---------------------------------------------------------------- */

/** Forecast horizon: 1-12 months, defaulting to 3. */
function populateHorizonOptions() {
  const DEFAULT_MONTHS = 3;
  for (let months = 1; months <= 12; months += 1) {
    const option = element("option", null, String(months));
    option.value = String(months);
    if (months === DEFAULT_MONTHS) {
      option.selected = true;
    }
    forecastHorizon.appendChild(option);
  }
}

populateHorizonOptions();
renderStepper();

const user = await requireRole(["admin", "finance_officer"]);
if (user) {
  renderTopBar(user);
}
