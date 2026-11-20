import test from "node:test";
import assert from "node:assert/strict";
import { transitions } from "./stages.mjs";
test("offer decisions require HR and terminal runs have no actions", () => {
  assert.deepEqual(transitions("selected", "recruiter"), []);
  assert.deepEqual(transitions("selected", "hr"), ["offer_sent"]);
  assert.deepEqual(transitions("complete", "hr"), []);
});
