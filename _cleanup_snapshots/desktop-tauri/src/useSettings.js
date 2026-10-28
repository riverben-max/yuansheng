import { reactive, ref } from "vue";
import { runSidecar } from "./sidecar";

export function useSettings() {
  const saving = ref(false);

  const state = reactive({
    scheduleEnabled: false,
    scheduleTime: "03:00",
    serverUrl: "",
    autoStartEnabled: false,
    shadowChromeAutoLaunch: false,
    exitRequiresConfirm: true,
    lastRunAt: "",
    lastPayloadSummary: "",
  });

  const settings = reactive({
    scheduleEnabled: false,
    scheduleTime: "03:00",
    serverUrl: "",
    autoStartEnabled: false,
    shadowChromeAutoLaunch: false,
    exitRequiresConfirm: true,
  });

  function applyState(nextState = {}) {
    Object.assign(state, nextState);
    Object.assign(settings, {
      scheduleEnabled: Boolean(nextState.scheduleEnabled),
      scheduleTime: nextState.scheduleTime || "03:00",
      serverUrl: nextState.serverUrl || "",
      autoStartEnabled: Boolean(nextState.autoStartEnabled),
      shadowChromeAutoLaunch: Boolean(nextState.shadowChromeAutoLaunch),
      exitRequiresConfirm: nextState.exitRequiresConfirm !== false,
    });
  }

  async function refreshState() {
    const result = await runSidecar("get_state");
    if (result?.ok) applyState(result.data);
    return result;
  }

  async function checkUpdate() {
    const result = await runSidecar("check_update");
    if (result?.ok && result.data?.updateAvailable) {
      return result.data;
    }
    return null;
  }

  async function saveSettings(onSuccess) {
    saving.value = true;
    try {
      const result = await runSidecar("save_settings", { ...settings });
      if (result?.ok) {
        applyState(result.data);
        if (onSuccess) onSuccess();
        return true;
      }
      return false;
    } finally {
      saving.value = false;
    }
  }

  return {
    saving,
    state,
    settings,
    applyState,
    refreshState,
    checkUpdate,
    saveSettings,
  };
}
