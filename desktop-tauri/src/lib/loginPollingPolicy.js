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

export function createLoginPollGate() {
  let generation = 0;
  let runningGeneration = 0;

  return {
    nextGeneration() {
      generation += 1;
      runningGeneration = 0;
      return generation;
    },
    stop() {
      generation += 1;
      runningGeneration = 0;
    },
    isCurrent(expectedGeneration) {
      return generation === expectedGeneration;
    },
    canRun(accountId, activeAccountId, expectedGeneration) {
      return Boolean(
        accountId
          && accountId === activeAccountId
          && generation === expectedGeneration
          && runningGeneration !== expectedGeneration,
      );
    },
    beginRun(expectedGeneration) {
      if (generation !== expectedGeneration || runningGeneration === expectedGeneration) {
        return false;
      }
      runningGeneration = expectedGeneration;
      return true;
    },
    endRun(expectedGeneration) {
      if (runningGeneration === expectedGeneration) {
        runningGeneration = 0;
      }
    },
  };
}
