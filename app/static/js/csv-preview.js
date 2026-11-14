/**
 * Minimal quote-aware CSV reader for the upload preview.
 *
 * Only the start of the file is read: a preview needs the header plus a
 * handful of rows, so there is no reason to pull a multi-megabyte file into
 * memory. The full file still goes to the server untouched.
 */

export const PREVIEW_ROW_COUNT = 5;

/** How much of the file to read for the preview. */
const PREVIEW_BYTES = 256 * 1024;

/**
 * Split CSV text into rows of fields.
 *
 * Quote handling follows the usual CSV convention: a field may be wrapped in
 * double quotes, a doubled "" inside a quoted field is a literal quote, and
 * commas and newlines inside quotes are part of the field.
 *
 * Parsing stops as soon as maxRows complete rows have been read, so every
 * row returned by that path is whole.
 *
 * @param {string} text
 * @param {number} maxRows
 * @returns {string[][]}
 */
export function parseCsv(text, maxRows = Number.POSITIVE_INFINITY) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  let index = 0;

  // A UTF-8 byte order mark would otherwise end up glued to the first
  // column name and break the column check.
  if (text.charCodeAt(0) === 0xfeff) {
    index = 1;
  }

  while (index < text.length) {
    const character = text[index];

    if (inQuotes) {
      if (character === '"') {
        if (text[index + 1] === '"') {
          field += '"';
          index += 2;
          continue;
        }
        inQuotes = false;
        index += 1;
        continue;
      }
      field += character;
      index += 1;
      continue;
    }

    if (character === '"') {
      inQuotes = true;
      index += 1;
      continue;
    }

    if (character === ",") {
      row.push(field);
      field = "";
      index += 1;
      continue;
    }

    if (character === "\r") {
      index += 1;
      continue;
    }

    if (character === "\n") {
      row.push(field);
      field = "";
      rows.push(row);
      row = [];
      if (rows.length >= maxRows) {
        return rows;
      }
      index += 1;
      continue;
    }

    field += character;
    index += 1;
  }

  // Final line when the text does not end with a newline.
  if (field !== "" || row.length > 0) {
    row.push(field);
    rows.push(row);
  }

  return rows;
}

/**
 * Read the header and the first rows of a CSV file.
 *
 * @param {File} file
 * @param {number} rowCount - data rows wanted
 * @returns {Promise<{columns: string[], rows: string[][]}>}
 */
export async function readCsvPreview(file, rowCount = PREVIEW_ROW_COUNT) {
  const truncated = file.size > PREVIEW_BYTES;
  const slice = truncated ? file.slice(0, PREVIEW_BYTES) : file;
  const text = await slice.text();

  const wanted = rowCount + 1; // header + data rows
  const rows = parseCsv(text, wanted);

  // Reaching `wanted` means every row came from a newline-terminated line.
  // Falling short on a truncated slice means the last row was cut mid-line.
  if (truncated && rows.length > 0 && rows.length < wanted) {
    rows.pop();
  }

  const header = rows.length > 0 ? rows[0] : [];
  return {
    columns: header.map((name) => name.trim()),
    rows: rows.slice(1, wanted),
  };
}
