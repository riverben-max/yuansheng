import { ref } from "vue";
import { ElMessage } from "element-plus/es/components/message/index.mjs";
import { normalizePlatform } from "../lib/platforms.js";
import { captureMessageState } from "../lib/captureMessage.js";

export function useCapture(callSidecar, refreshState, applyState) {
  const captureBusy = ref(false);

  function showCaptureMessage(data = {}) {
    const msgState = captureMessageState(data);
    ElMessage[msgState.type](msgState.message);
  }

  async function runCapture(command, payload) {
    captureBusy.value = true;
    try {
      const result = await callSidecar(command, payload);
      if (result?.ok) {
        if (result.data?.state) applyState(result.data.state);
        await refreshState();
        showCaptureMessage(result.data);
      }
    } finally {
      captureBusy.value = false;
    }
  }

  async function captureAll(platform, platformCards) {
    const action = platformCards.value.find(
      (card) => card.platform === normalizePlatform(platform),
    )?.action;
    if (action?.disabled) {
      return { blocked: true, hint: action.hint || "请先登录全部启用账号" };
    }
    await runCapture("capture_all", {});
    return { blocked: false };
  }

  async function captureAccount(account) {
    await runCapture("capture_account", { accountId: account.id });
  }

  return { captureBusy, captureAll, captureAccount, runCapture };
}
