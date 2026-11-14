/**
 * Workspace, step 1: choose a CSV, preview it, check its columns, and send
 * it to the ingestion endpoint.
 *
 * Steps 2 and 3 (run analysis, results) are filled in by the next chunk.
 * Every value that comes back from the API is written with textContent.
 */

import { apiUpload, requireRole } from "./api.js";
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

/** The file waiting to be uploaded, and whether its columns check out. */
let selectedFile = null;
let columnsComplete = false;

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

// A file dropped outside the zone would otherwise navigate away from the app.
["dragover", "drop"].forEach((name) => {
  window.addEventListener(name, (event) => {
    if (!dropzone.contains(event.target)) {
      event.preventDefault();
    }
  });
});

/* --- Boot ---------------------------------------------------------------- */

const user = await requireRole(["admin", "finance_officer"]);
if (user) {
  renderTopBar(user);
}
