import assert from "node:assert/strict";
import test from "node:test";
import { toCsv } from "./csv.js";

test("toCsv quotes commas and quotes, blanks nulls, and defuses formula-like text", () => {
  assert.equal(
    toCsv([["Date", "Sky"], ["2026-11-01", 'FEW 50, "BKN" 250'], [-4.5, null], ["-RA", "=1+1"]]),
    ["Date,Sky", '2026-11-01,"FEW 50, ""BKN"" 250"', "-4.5,", "'-RA,'=1+1"].join("\n"),
  );
});
