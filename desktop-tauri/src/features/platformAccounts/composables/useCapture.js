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
    const result = await callSidecar(command, payload);
    if (result?.ok) {
      if (result.data?.state) applyState(result.data.state);
      await refreshState();
      showCaptureMessage(result.data);
    }
  }

  async function captureAll(platform, platformCards) {
    if (captureBusy.value) return { blocked: true, hint: "采集进行中，请稍后再试" };
    const action = platformCards.value.find(
      (card) => card.platform === normalizePlatform(platform),
    )?.action;
    if (action?.disabled) {
      return { blocked: true, hint: action.hint || "请先登录全部启用账号" };
    }
    captureBusy.value = true;
    try {
      await runCapture("capture_all", {});
    } finally {
      captureBusy.value = false;
    }
    return { blocked: false };
  }

  async function captureAccount(account) {
    if (captureBusy.value) return { blocked: true, hint: "采集进行中，请稍后再试" };
    captureBusy.value = true;
    try {
      await runCapture("capture_account", { accountId: account.id });
    } finally {
      captureBusy.value = false;
    }
    return { blocked: false };
  }

  async function captureAccountDirect(account) {
    if (captureBusy.value) return { blocked: true, hint: "采集进行中，请稍后再试" };
    captureBusy.value = true;
    try {
      await runCapture("capture_account_direct", { accountId: account.id });
    } finally {
      captureBusy.value = false;
    }
    return { blocked: false };
  }

  return { captureBusy, captureAll, captureAccount, captureAccountDirect, runCapture };
}
