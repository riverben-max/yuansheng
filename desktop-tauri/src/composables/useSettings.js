import { reactive, ref } from "vue";
import { ElMessage } from "element-plus/es/components/message/index.mjs";

export function useSettings(callSidecar) {
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

  const accounts = ref([]);

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
    accounts.value = Array.isArray(nextState.loginAccounts) ? nextState.loginAccounts : [];
  }

  async function refreshState() {
    const result = await callSidecar("get_state");
    if (result?.ok) applyState(result.data);
  }

  async function saveSettings() {
    saving.value = true;
    try {
      const result = await callSidecar("save_settings", { ...settings });
      if (result?.ok) {
        applyState(result.data);
        ElMessage.success("设置已保存");
      }
    } finally {
      saving.value = false;
    }
  }

  return { state, settings, accounts, saving, applyState, refreshState, saveSettings };
}
