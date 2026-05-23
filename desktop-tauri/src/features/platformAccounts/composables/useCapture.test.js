import test from "node:test";
import assert from "node:assert/strict";

import { useCapture } from "./useCapture.js";

test("captureAll sends selected platform to sidecar", async () => {
  const calls = [];
  const callSidecar = async (command, payload) => {
    calls.push({ command, payload });
    return { ok: false };
  };
  const refreshState = async () => {};
  const applyState = () => {};
  const platformCards = {
    value: [{ platform: "jd", action: { disabled: false } }],
  };

  const { captureAll } = useCapture(callSidecar, refreshState, applyState);
  const result = await captureAll("jd", platformCards);

  assert.deepEqual(result, { blocked: false });
  assert.deepEqual(calls, [{ command: "capture_all", payload: { platform: "jd" } }]);
});

test("captureAll trims and lowercases selected platform", async () => {
  const calls = [];
  const callSidecar = async (command, payload) => {
    calls.push({ command, payload });
    return { ok: false };
  };
  const platformCards = {
    value: [{ platform: "jd", action: { disabled: false } }],
  };

  const { captureAll } = useCapture(callSidecar, async () => {}, () => {});
  const result = await captureAll(" JD ", platformCards);

  assert.deepEqual(result, { blocked: false });
  assert.deepEqual(calls, [{ command: "capture_all", payload: { platform: "jd" } }]);
});

test("captureAccount skips disabled account before calling sidecar", async () => {
  const calls = [];
  const callSidecar = async (command, payload) => {
    calls.push({ command, payload });
    return { ok: false };
  };

  const { captureAccount } = useCapture(callSidecar, async () => {}, () => {});
  const result = await captureAccount({ id: "a1", enabled: false });

  assert.equal(result.blocked, true);
  assert.match(result.hint, /已禁用/);
  assert.deepEqual(calls, []);
});
