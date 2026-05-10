import assert from "node:assert/strict";
import test from "node:test";

import {
  LOGIN_POLL_FIRST_DELAY_MS,
  LOGIN_POLL_REQUEST_TIMEOUT_MS,
  loginPollFailureState,
} from "./loginPollingPolicy.js";

test("login polling waits before first detection and allows slow sidecar attach", () => {
  assert.equal(LOGIN_POLL_FIRST_DELAY_MS, 3000);
  assert.equal(LOGIN_POLL_REQUEST_TIMEOUT_MS, 25 * 1000);
});

test("single poll timeout stays in recoverable waiting state", () => {
  assert.deepEqual(
    loginPollFailureState({
      timeout: true,
      message: "登录检测超时，请重新点击该账号登录",
    }),
    { recoverable: true, status: "等待登录检测", danger: false },
  );
});

test("tauri sidecar timeout during poll stays recoverable", () => {
  assert.deepEqual(
    loginPollFailureState({
      message: "sidecar 执行超时（20 秒，PID=1234），已终止。",
    }),
    { recoverable: true, status: "等待登录检测", danger: false },
  );
});

test("explicit login detection failure remains terminal", () => {
  assert.deepEqual(
    loginPollFailureState({ message: "登录检测失败" }),
    { recoverable: false, status: "登录检测失败", danger: true },
  );
});
