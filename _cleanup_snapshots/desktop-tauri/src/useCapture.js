import { ref } from "vue";
import { runSidecar } from "./sidecar";

export function useCapture({ onStateUpdate, isAccountReady }) {
  const captureBusy = ref(false);

  async function runCapture(command, payload, { onSuccess, onError } = {}) {
    captureBusy.value = true;
    try {
      const result = await runSidecar(command, payload);
      if (result?.ok) {
        if (result.data?.state) onStateUpdate(result.data.state);
        if (onSuccess) onSuccess(result.data);
        return result;
      }
      if (onError) onError(result);
      return result;
    } catch (error) {
      if (onError) onError({ ok: false, message: String(error) });
      return { ok: false, message: String(error) };
    } finally {
      captureBusy.value = false;
    }
  }

  async function captureAccount(account, { onMessage } = {}) {
    const isReady = typeof isAccountReady === "function" ? isAccountReady(account) : true;
    if (!isReady) {
      if (onMessage) onMessage("warning", "请先登录该账号");
      return;
    }
    return runCapture("capture_account", { accountId: account.id }, {
      onSuccess: () => onMessage?.("success", "采集完成"),
    });
  }

  async function captureAll({ onMessage, enabledAccounts, loggedInCount } = {}) {
    const enabled = enabledAccounts || [];
    const ready = loggedInCount || 0;
    if (enabled.length > 0 && ready !== enabled.length) {
      if (onMessage) onMessage("warning", "请先登录全部启用账号");
      return;
    }
    return runCapture("capture_all", {}, {
      onSuccess: (data) => {
        const results = Array.isArray(data?.results) ? data.results : [];
        if (!results.length) return onMessage?.("success", "采集完成");
        const okCount = results.filter((item) => item.ok).length;
        if (okCount === results.length) onMessage?.("success", "采集完成");
        else if (okCount > 0) onMessage?.("warning", "部分账号采集失败");
        else onMessage?.("error", "采集失败");
      },
    });
  }

  return {
    captureBusy,
    runCapture,
    captureAccount,
    captureAll,
  };
}
