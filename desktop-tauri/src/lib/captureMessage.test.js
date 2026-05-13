import test from "node:test";
import assert from "node:assert/strict";

import { captureMessageState } from "./captureMessage.js";

test("shows success only when captured accounts have no failure reason", () => {
  assert.deepEqual(captureMessageState({ results: [{ ok: true, lastFailureReason: "" }] }), {
    type: "success",
    message: "采集完成",
  });
});

test("shows missing platform employee account instead of generic success", () => {
  assert.deepEqual(
    captureMessageState({
      results: [
        {
          ok: true,
          lastFailureReason: "平台未配置客服账号",
          lastCaptureSummary: { ok: true, uploaded: false },
        },
      ],
    }),
    {
      type: "warning",
      message: "平台未配置客服账号",
    },
  );
});

test("keeps partial failure wording when clean success and issue both exist", () => {
  assert.deepEqual(
    captureMessageState({
      results: [
        { ok: true, lastFailureReason: "" },
        { ok: true, lastFailureReason: "平台未配置客服账号" },
      ],
    }),
    {
      type: "warning",
      message: "部分账号采集失败",
    },
  );
});

test("keeps skipped and full failure messages", () => {
  assert.deepEqual(captureMessageState({ results: [{ skipped: true, message: "采集暂未接入" }] }), {
    type: "info",
    message: "采集暂未接入",
  });
  assert.deepEqual(captureMessageState({ results: [{ ok: false, message: "Cookie 失效" }] }), {
    type: "warning",
    message: "Cookie 失效",
  });
});
