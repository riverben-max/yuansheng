import test from "node:test";
import assert from "node:assert/strict";

import { buildPlatformSummaries, isAccountCaptureReady, platformActionState, platformSummaryText, uploadFailureText } from "./platformOverview.js";

const accounts = [
  {
    id: "legacy-qn",
    enabled: true,
    loginStatus: "已登录",
    cookieStatus: "已保存",
    lastCaptureAt: "2026-05-10 09:00:00",
    lastResult: "采集成功",
  },
  {
    id: "qn-waiting",
    platform: "qn",
    enabled: true,
    loginStatus: "待登录",
    lastCaptureSummary: {
      ok: true,
      uploaded: true,
      capturedAt: "2026-05-11 09:00:00",
    },
  },
  {
    id: "jd-ready",
    platform: "jd",
    enabled: true,
    loginStatus: "已登录",
    cookieStatus: "已保存",
    lastCaptureSummary: {
      ok: true,
      uploaded: false,
      uploadMessage: "演示上传失败",
      capturedAt: "2026-05-12 10:00:00",
    },
  },
  {
    id: "pdd-ready",
    platform: "pdd",
    enabled: true,
    loginStatus: "已登录",
    cookieStatus: "已保存",
  },
];

test("builds fixed qn, jd and pdd platform summaries and treats missing platform as qn", () => {
  const summaries = buildPlatformSummaries(accounts);

  assert.deepEqual(summaries.map((item) => item.platform), ["qn", "jd", "pdd"]);
  assert.equal(summaries[0].accountCount, 2);
  assert.equal(summaries[0].enabledCount, 2);
  assert.equal(summaries[0].loggedInCount, 1);
  assert.equal(summaries[1].accountCount, 1);
  assert.equal(summaries[1].enabledCount, 1);
  assert.equal(summaries[1].loggedInCount, 1);
  assert.equal(summaries[2].accountCount, 1);
  assert.equal(summaries[2].enabledCount, 1);
  assert.equal(summaries[2].loggedInCount, 1);
  assert.equal(summaries[2].supportsCapture, false);
});

test("uses the latest capture result inside each platform", () => {
  const [qnSummary, jdSummary] = buildPlatformSummaries(accounts);

  assert.equal(qnSummary.latestCaptureAt, "2026-05-11 09:00:00");
  assert.equal(qnSummary.latestResultText, "采集成功");
  assert.equal(jdSummary.latestCaptureAt, "2026-05-12 10:00:00");
  assert.equal(jdSummary.latestResultText, "上传失败");
});

test("shows missing platform employee account instead of generic upload failure", () => {
  const [, jdSummary] = buildPlatformSummaries([
    {
      id: "jd-no-employee",
      platform: "jd",
      enabled: true,
      loginStatus: "采集成功",
      lastFailureReason: "平台未配置客服账号",
      lastCaptureSummary: {
        ok: true,
        uploaded: false,
        uploadMessage: "服务端上传失败：未找到员工账号映射：subAccount=未分配，请先在系统用户中创建对应客服账号",
        capturedAt: "2026-05-12 10:00:00",
      },
    },
  ]);

  assert.equal(jdSummary.latestResultText, "平台未配置客服账号");
  assert.equal(uploadFailureText("服务端上传失败：未找到员工账号映射：subAccount=未分配"), "平台未配置客服账号");
  assert.equal(uploadFailureText("服务端上传失败：连接超时"), "上传失败");
});

test("formats compact platform summary text", () => {
  const [qnSummary] = buildPlatformSummaries(accounts);

  assert.equal(platformSummaryText(qnSummary), "已登录 1 / 启用 2");
});

test("blocks a platform until its enabled accounts are logged in and enables ready jd capture", () => {
  const [qnSummary, jdSummary, pddSummary] = buildPlatformSummaries(accounts);

  assert.deepEqual(platformActionState(qnSummary), {
    disabled: true,
    reason: "need-login",
    buttonText: "采集千牛启用账号",
    hint: "请先登录全部启用千牛账号",
  });
  assert.deepEqual(platformActionState(jdSummary), {
    disabled: false,
    reason: "ready",
    buttonText: "采集京东启用账号",
    hint: "",
  });
  assert.deepEqual(platformActionState(pddSummary), {
    disabled: true,
    reason: "unsupported",
    buttonText: "采集拼多多启用账号",
    hint: "拼多多采集暂未接入",
  });
});

test("enables platform action when every enabled account for that platform is logged in", () => {
  const [qnSummary] = buildPlatformSummaries([
    { id: "qn-1", platform: "qn", enabled: true, loginStatus: "已登录", cookieStatus: "已保存" },
    { id: "qn-2", platform: "qn", enabled: false, loginStatus: "待登录" },
  ]);

  assert.deepEqual(platformActionState(qnSummary), {
    disabled: false,
    reason: "ready",
    buttonText: "采集千牛启用账号",
    hint: "",
  });
});

test("does not treat cookie diagnostics without saved cookie as logged in", () => {
  const account = {
    id: "qn-diagnostic-only",
    platform: "qn",
    enabled: true,
    loginStatus: "登录窗口已关闭",
    cookieStatus: "未登录",
    cookieSummary: "长度=914，PASS_ID=无",
  };
  const [qnSummary] = buildPlatformSummaries([account]);

  assert.equal(isAccountCaptureReady(account), false);
  assert.equal(qnSummary.loggedInCount, 0);
  assert.deepEqual(platformActionState(qnSummary), {
    disabled: true,
    reason: "need-login",
    buttonText: "采集千牛启用账号",
    hint: "请先登录全部启用千牛账号",
  });
});
