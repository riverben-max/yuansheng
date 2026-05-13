import { ACCOUNT_PLATFORM_OPTIONS, normalizePlatform, platformLabel } from "./accountMatrix.js";

export function buildPlatformSummaries(accounts) {
  const source = Array.isArray(accounts) ? accounts : [];
  return ACCOUNT_PLATFORM_OPTIONS.map((option) => {
    const platformAccounts = source.filter((account) => normalizePlatform(account?.platform) === option.value);
    const enabledAccounts = platformAccounts.filter((account) => account.enabled);
    const latestAccount = findLatestCaptureAccount(platformAccounts);
    return {
      platform: option.value,
      label: platformLabel(option.value),
      accountCount: platformAccounts.length,
      enabledCount: enabledAccounts.length,
      loggedInCount: enabledAccounts.filter(isAccountCaptureReady).length,
      latestCaptureAt: latestAccount ? accountCaptureTime(latestAccount) : "",
      latestResultText: latestAccount ? accountResultText(latestAccount) : "尚未采集",
    };
  });
}

export function platformSummaryText(summary) {
  return `已登录 ${summary?.loggedInCount || 0} / 启用 ${summary?.enabledCount || 0}`;
}

export function platformActionState(summary) {
  const label = platformLabel(summary?.platform);
  const buttonText = `采集${label}启用账号`;
  if (!summary?.enabledCount) {
    return {
      disabled: true,
      reason: "no-enabled",
      buttonText,
      hint: `请先启用${label}账号`,
    };
  }
  if (summary.loggedInCount !== summary.enabledCount) {
    return {
      disabled: true,
      reason: "need-login",
      buttonText,
      hint: `请先登录全部启用${label}账号`,
    };
  }
  return {
    disabled: false,
    reason: "ready",
    buttonText,
    hint: "",
  };
}

function findLatestCaptureAccount(accounts) {
  return accounts
    .filter((account) => accountCaptureTime(account))
    .map((account) => ({ account, time: Date.parse(accountCaptureTime(account).replace(/-/g, "/")) || 0 }))
    .sort((left, right) => right.time - left.time)[0]?.account;
}

function accountCaptureTime(account) {
  return account?.lastCaptureSummary?.capturedAt || account?.lastCaptureAt || "";
}

export function isAccountCaptureReady(account) {
  const status = String(account?.loginStatus || "").trim();
  const cookieStatus = String(account?.cookieStatus || "").trim();
  return account?.enabled && (["已登录", "采集成功"].includes(status) || cookieStatus === "已保存" || Boolean(account?.cookieUpdatedAt || account?.cookieSummary));
}

export function accountResultText(account) {
  if (account?.lastCaptureSummary?.ok) {
    return account.lastCaptureSummary.uploaded ? "采集成功" : uploadFailureText(account.lastCaptureSummary.uploadMessage);
  }
  const reason = String(account?.lastFailureReason || "").trim();
  if (reason) return reason;
  const status = String(account?.loginStatus || "").trim();
  if (status === "采集暂未接入") return "采集暂未接入";
  if (status === "需要重新登录") return "需要重新登录";
  if (status === "采集失败") return "采集失败";
  const result = String(account?.lastResult || "").trim();
  if (result === "京东采集暂未接入") return "采集暂未接入";
  if (result) return "采集成功";
  return "尚未采集";
}

export function uploadFailureText(uploadMessage) {
  const message = String(uploadMessage || "");
  if (message.includes("未找到员工账号映射")) return "平台未配置客服账号";
  return "上传失败";
}
