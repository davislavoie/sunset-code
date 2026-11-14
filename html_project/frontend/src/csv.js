// CSV text for downloads (Score tracker's Data tab).

/** One CSV cell. Text a spreadsheet would run as a formula (airport weather like "-RA") gets a leading quote. */
function csvCell(v) {
  if (v == null) return "";
  const text = typeof v === "string" && /^[=+\-@]/.test(v) ? `'${v}` : String(v);
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

export const toCsv = (lines) => lines.map((line) => line.map(csvCell).join(",")).join("\n");
