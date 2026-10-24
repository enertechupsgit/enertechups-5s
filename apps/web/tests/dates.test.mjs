import test from "node:test";
import assert from "node:assert/strict";
import {
  parseDate,
  timestamp,
  dateLabel,
} from "../src/components/Workspace/dates.ts";
test("naive API timestamps are UTC", () =>
  assert.equal(timestamp("2026-10-24T10:00:00"), Date.UTC(2026, 9, 24, 10)));
test("explicit offsets are preserved", () =>
  assert.equal(
    timestamp("2026-10-24T15:30:00+05:30"),
    timestamp("2026-10-24T10:00:00Z"),
  ));
test("calendar dates retain their day", () => {
  assert.equal(parseDate("2026-10-24").getDate(), 24);
  assert.equal(dateLabel(null), "No due date");
});
