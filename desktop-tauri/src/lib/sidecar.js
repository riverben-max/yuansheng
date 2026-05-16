import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { normalizePlatform } from "../features/platformAccounts/lib/platforms.js";

const inTauri = typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;

const demoState = {
  scheduleEnabled: true,
  scheduleTime: "03:00",
  serverUrl: "http://120.27.22.50",
  autoStartEnabled: true,
  shadowChromeAutoLaunch: false,
  exitRequiresConfirm: true,
  lastRunAt: "",
  lastPayloadSummary: "尚未采集",
  loginAccounts: [
    {
      id: "default",
      enabled: true,
      platform: "qn",
      shopName: "",
      displayName: "默认账号",
      loginHint: "",
      chromePort: 0,
      loginStatus: "待验证",
      lastCaptureAt: "",
      lastResult: "",
      cookieStatus: "未登录",
    },
  ],
};

export async function subscribeSidecarEvents(handler) {
  if (!inTauri) return () => {};
  return listen("sidecar-event", (event) => handler(event.payload));
}

export async function runSidecar(command, payload = {}) {
  if (!inTauri) {
    return runDemoCommand(command, payload);
  }
  return invoke("sidecar_command", { command, payload });
}

function runDemoCommand(command, payload) {
  if (command === "get_state") {
    return Promise.resolve({ ok: true, data: structuredClone(demoState), events: [] });
  }
  if (command === "save_settings") {
    Object.assign(demoState, payload);
    return Promise.resolve({ ok: true, data: structuredClone(demoState), events: [] });
  }
  if (command === "account_create") {
    const account = {
      id: `account-${Date.now()}`,
      enabled: true,
      platform: normalizePlatform(payload.platform),
      shopName: payload.shopName || "",
      displayName: payload.displayName || "新登录账户",
      loginHint: payload.loginHint || "",
      chromePort: 0,
      loginStatus: "待登录",
      lastCaptureAt: "",
      lastResult: "",
      cookieStatus: "未登录",
    };
    demoState.loginAccounts.push(account);
    return Promise.resolve({ ok: true, data: account, events: [] });
  }
  if (command === "account_update") {
    const account = demoState.loginAccounts.find((item) => item.id === payload.id);
    if (account) {
      Object.assign(account, payload, {
        platform: normalizePlatform(payload.platform || account.platform),
        shopName: payload.shopName || "",
      });
    }
    return Promise.resolve({ ok: true, data: account, events: [] });
  }
  if (command === "account_delete") {
    demoState.loginAccounts = demoState.loginAccounts.filter((item) => item.id !== payload.id);
    return Promise.resolve({ ok: true, data: { id: payload.id }, events: [] });
  }
  if (command === "start_login") {
    const account = demoState.loginAccounts.find((item) => item.id === payload.accountId);
    if (account) account.loginStatus = "等待登录";
    return Promise.resolve({ ok: true, data: { browser: { launched: true } }, events: [] });
  }
  if (command === "poll_login") {
    const account = demoState.loginAccounts.find((item) => item.id === payload.accountId);
    if (account) {
      account.loginStatus = "已登录";
      account.cookieStatus = "已保存";
      account.cookieUpdatedAt = new Date().toLocaleString("zh-CN", { hour12: false });
    }
    return Promise.resolve({ ok: true, data: { loggedIn: true, status: "已登录", state: structuredClone(demoState) }, events: [] });
  }
  if (command === "capture_account" || command === "capture_all") {
    const now = new Date().toLocaleString("zh-CN", { hour12: false });
    const results = [];
    demoState.loginAccounts.forEach((account) => {
      if (command === "capture_account" && account.id !== payload.accountId) return;
      account.loginStatus = "采集成功";
      account.lastCaptureAt = now;
      account.lastResult = "演示模式采集成功";
      account.lastFailureReason = "";
      account.lastCaptureSummary = {
        ok: true,
        displayName: account.displayName,
        loginAccount: "远盛电商",
        subAccount: account.displayName,
        recordDate: "2026-05-09",
        capturedAt: now,
        uploaded: true,
        uploadMessage: "演示模式上传成功",
        metrics: {
          consultationCount: 12,
          receiveCount: 10,
          validReceiveCount: 9,
          inquiryCount: 6,
          conversionRate: 33.33,
          firstReplyTime: 8,
          avgReplyTime: 18,
          wwReplyRate: 99.5,
          satisfaction: 100,
        },
      };
      results.push({
        accountId: account.id,
        displayName: account.displayName,
        ok: true,
        lastCaptureSummary: account.lastCaptureSummary,
      });
    });
    return Promise.resolve({
      ok: true,
      data: { batch: true, results, state: structuredClone(demoState) },
      events: [
        { type: "status", status: "采集中", danger: false },
        { type: "log", time: new Date().toLocaleTimeString("zh-CN", { hour12: false }), message: "演示模式：采集完成。" },
        { type: "status", status: "待命", danger: false },
      ],
    });
  }
  return Promise.resolve({
    ok: true,
    data: { state: structuredClone(demoState), results: [] },
    events: [
      { type: "status", status: "采集中", danger: false },
      { type: "log", time: new Date().toLocaleTimeString("zh-CN", { hour12: false }), message: "演示模式：等待 Tauri 运行环境连接 sidecar。" },
      { type: "status", status: "待命", danger: false },
    ],
  });
}
