/**
 * Quote-aware CSV reader for the upload panel.
 *
 * The file is read in chunks and parsed incrementally so that the whole
 * dataset can be summarised (record count, column count, distinct
 * departments) without pulling a multi-megabyte string into memory in one
 * go and without blocking the page: each chunk is a separate task, so the
 * browser stays responsive while a 20 MB file is scanned. The full file
 * still goes to the server untouched.
 */

export const PREVIEW_ROW_COUNT = 5;

/** How much of the file to decode per task. */
const READ_CHUNK_BYTES = 1024 * 1024;

/**
 * An incremental CSV row scanner.
 *
 * Quote handling follows the usual CSV convention: a field may be wrapped in
 * double quotes, a doubled "" inside a quoted field is a literal quote, and
 * commas and newlines inside quotes are part of the field. State is kept
 * between push() calls, so a quoted field, an escaped quote or a CRLF split
 * across a chunk boundary is still read correctly.
 *
 * @param {(row: string[]) => void} onRow - called once per complete row
 */
function createRowScanner(onRow) {
  let field = "";
  let row = [];
  let inQuotes = false;
  // A '"' seen inside a quoted field: the next character decides whether it
  // closed the field or was the first half of an escaped "".
  let quotePending = false;
  let atFileStart = true;

  function endField() {
    row.push(field);
    field = "";
  }

  function endRow() {
    endField();
    onRow(row);
    row = [];
  }

  return {
    push(text) {
      let index = 0;

      if (atFileStart && text.length > 0) {
        atFileStart = false;
        // A UTF-8 byte order mark would otherwise be glued to the first
        // column name and break the column check. TextDecoder normally
        // strips it; this covers the case where it does not.
        if (text.charCodeAt(0) === 0xfeff) {
          index = 1;
        }
      }

      while (index < text.length) {
        const character = text[index];

        if (quotePending) {
          quotePending = false;
          if (character === '"') {
            field += '"';
            index += 1;
            continue;
          }
          // The quote closed the field; fall through and read this
          // character as unquoted text.
          inQuotes = false;
        }

        if (inQuotes) {
          if (character === '"') {
            quotePending = true;
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
          endField();
          index += 1;
          continue;
        }

        if (character === "\r") {
          index += 1;
          continue;
        }

        if (character === "\n") {
          endRow();
          index += 1;
          continue;
        }

        field += character;
        index += 1;
      }
    },

    /** Close the final row when the file does not end with a newline. */
    end() {
      quotePending = false;
      inQuotes = false;
      if (field !== "" || row.length > 0) {
        endRow();
      }
    },
  };
}

/**
 * Read a CSV file end to end: its header, the first few rows for the
 * preview, how many data rows it holds, and how many distinct values a
 * named column contains.
 *
 * Nothing about the dataset is assumed: every figure is counted from the
 * file itself.
 *
 * @param {File} file
 * @param {{previewRows?: number, distinctColumn?: string}} options
 * @returns {Promise<{columns: string[], rows: string[][], rowCount: number,
 *                    distinctCount: number|null}>}
 */
export async function readCsvDataset(file, options) {
  const settings = options || {};
  const previewRows =
    settings.previewRows === undefined ? PREVIEW_ROW_COUNT : settings.previewRows;
  const distinctColumn = settings.distinctColumn;

  let header = null;
  let distinctIndex = -1;
  const rows = [];
  const distinctValues = new Set();
  let rowCount = 0;

  const scanner = createRowScanner((row) => {
    if (header === null) {
      header = row.map((name) => name.trim());
      if (distinctColumn) {
        distinctIndex = header.indexOf(distinctColumn);
      }
      return;
    }

    // A trailing blank line parses as a single empty field. It is not a record.
    if (row.length === 1 && row[0] === "") {
      return;
    }

    rowCount += 1;
    if (rows.length < previewRows) {
      rows.push(row);
    }
    if (distinctIndex >= 0) {
      const value = (row[distinctIndex] || "").trim();
      if (value !== "") {
        distinctValues.add(value);
      }
    }
  });

  // One TextDecoder across every chunk, in streaming mode, so a multi-byte
  // character straddling a chunk boundary is not corrupted.
  const decoder = new TextDecoder("utf-8");
  for (let offset = 0; offset < file.size; offset += READ_CHUNK_BYTES) {
    const buffer = await file.slice(offset, offset + READ_CHUNK_BYTES).arrayBuffer();
    scanner.push(decoder.decode(buffer, { stream: true }));
  }
  scanner.push(decoder.decode());
  scanner.end();

  return {
    columns: header === null ? [] : header,
    rows: rows,
    rowCount: rowCount,
    distinctCount: distinctIndex >= 0 ? distinctValues.size : null,
  };
}
