export const LOGIN_POLL_INTERVAL_MS = 3000;
export const LOGIN_POLL_FIRST_DELAY_MS = 3000;
export const LOGIN_POLL_TIMEOUT_MS = 5 * 60 * 1000;
export const LOGIN_POLL_REQUEST_TIMEOUT_MS = 25 * 1000;

export function loginPollFailureState(result = {}) {
  const message = String(result?.message || "");
  if (result?.timeout || message.includes("sidecar 执行超时")) {
    return { recoverable: true, status: "等待登录检测", danger: false };
  }
  return { recoverable: false, status: "登录检测失败", danger: true };
}
