import { computed, ref } from "vue";
import { ElMessage } from "element-plus/es/components/message/index.mjs";
import {
  LOGIN_POLL_FIRST_DELAY_MS,
  LOGIN_POLL_INTERVAL_MS,
  LOGIN_POLL_REQUEST_TIMEOUT_MS,
  LOGIN_POLL_TIMEOUT_MS,
  createLoginPollGate,
  loginPollFailureState,
} from "../lib/loginPollingPolicy.js";
import { isAccountCaptureReady } from "../lib/platformOverview.js";

export function useLoginPolling(callSidecar, refreshState, accounts) {
  const loginBusy = ref(false);
  const runtimeStatus = ref("待命");
  const statusDanger = ref(false);
  const activeLoginAccountId = ref("");

  let loginPollTimer = null;
  let loginPollFirstTimer = null;
  let loginPollStartedAt = 0;
  const loginPollGate = createLoginPollGate();

  const enabledAccounts = computed(() => accounts.value.filter((a) => a.enabled));
  const loggedInEnabledAccounts = computed(() => enabledAccounts.value.filter(isAccountCaptureReady));
  const allEnabledAccountsLoggedIn = computed(
    () => enabledAccounts.value.length > 0 && loggedInEnabledAccounts.value.length === enabledAccounts.value.length,
  );
  const loginSummaryStatus = computed(() => {
    if (!enabledAccounts.value.length) return "无启用账号";
    if (allEnabledAccountsLoggedIn.value) return "已全部登录";
    if (loggedInEnabledAccounts.value.length > 0) return "部分已登录";
    return "待登录";
  });

  function syncRuntimeStatusFromAccounts() {
    runtimeStatus.value = loginSummaryStatus.value;
    statusDanger.value = loginSummaryStatus.value === "待登录";
  }

  function stopLoginPolling() {
    loginPollGate.stop();
    if (loginPollFirstTimer) {
      window.clearTimeout(loginPollFirstTimer);
      loginPollFirstTimer = null;
    }
    if (loginPollTimer) {
      window.clearInterval(loginPollTimer);
      loginPollTimer = null;
    }
    activeLoginAccountId.value = "";
    loginBusy.value = false;
  }

  function withTimeout(promise, timeoutMs, timeoutResult) {
    let timer = null;
    const timeoutPromise = new Promise((resolve) => {
      timer = window.setTimeout(() => resolve(timeoutResult), timeoutMs);
    });
    return Promise.race([promise, timeoutPromise]).finally(() => {
      if (timer) window.clearTimeout(timer);
    });
  }

  async function pollLoginOnce(accountId, gen) {
    if (!loginPollGate.canRun(accountId, activeLoginAccountId.value, gen)) return;
    if (Date.now() - loginPollStartedAt > LOGIN_POLL_TIMEOUT_MS) {
      stopLoginPolling();
      runtimeStatus.value = "登录超时";
      statusDanger.value = true;
      ElMessage.warning("登录等待超时，请重新点击该账号登录");
      return;
    }

    if (!loginPollGate.beginRun(gen)) return;
    try {
      const result = await withTimeout(
        callSidecar("poll_login", { accountId }, { suppressError: true }),
        LOGIN_POLL_REQUEST_TIMEOUT_MS,
        { ok: false, timeout: true, message: "登录检测超时，请重新点击该账号登录" },
      );
      if (!loginPollGate.isCurrent(gen)) return;
      if (!result?.ok) {
        const failure = loginPollFailureState(result);
        runtimeStatus.value = failure.status;
        statusDanger.value = failure.danger;
        if (!failure.recoverable) {
          stopLoginPolling();
          ElMessage.warning(result?.message || "登录检测失败");
        }
        return;
      }
      if (result.data?.state) {
        // applyState is called by the caller if provided, but the composable
        // doesn't own state. Instead we call refreshState.
        await refreshState();
      }
      if (result.data?.loggedIn) {
        stopLoginPolling();
        syncRuntimeStatusFromAccounts();
        statusDanger.value = false;
        ElMessage.success("登录成功，Cookie 已保存");
        return;
      }
      if (!loginPollGate.isCurrent(gen)) return;
      const status = result.data?.status || "等待扫码";
      runtimeStatus.value = status;
      statusDanger.value = !["等待扫码", "等待登录检测", "正在清理临时浏览器"].includes(status);
      if (status === "登录窗口已关闭" || status === "登录检测失败") {
        stopLoginPolling();
        ElMessage.warning(result.data?.message || status);
      }
    } finally {
      loginPollGate.endRun(gen);
    }
  }

  function beginLoginPolling(accountId) {
    activeLoginAccountId.value = accountId;
    loginPollStartedAt = Date.now();
    const gen = loginPollGate.nextGeneration();
    loginPollFirstTimer = window.setTimeout(() => {
      loginPollFirstTimer = null;
      if (!loginPollGate.isCurrent(gen)) return;
      void pollLoginOnce(accountId, gen);
      loginPollTimer = window.setInterval(() => {
        if (!loginPollGate.isCurrent(gen)) {
          window.clearInterval(loginPollTimer);
          loginPollTimer = null;
          return;
        }
        void pollLoginOnce(accountId, gen);
      }, LOGIN_POLL_INTERVAL_MS);
    }, LOGIN_POLL_FIRST_DELAY_MS);
  }

  async function startLogin(account, activeTabRef) {
    if (loginBusy.value) return;
    if (!account?.id) {
      ElMessage.warning("请先在用户管理中选择一个登录账号");
      if (activeTabRef) activeTabRef.value = "accounts";
      return;
    }
    stopLoginPolling();
    loginBusy.value = true;
    let keepBusyForPolling = false;
    try {
      const payload = { accountId: account.id };
      const result = await callSidecar("start_login", payload);
      if (result?.ok) {
        runtimeStatus.value = "等待扫码";
        statusDanger.value = false;
        activeLoginAccountId.value = account.id;
        keepBusyForPolling = true;
        beginLoginPolling(account.id);
        ElMessage.success("已打开登录窗口");
      }
    } finally {
      if (!keepBusyForPolling) loginBusy.value = false;
    }
  }

  return {
    loginBusy,
    runtimeStatus,
    statusDanger,
    activeLoginAccountId,
    loginSummaryStatus,
    startLogin,
    beginLoginPolling,
    stopLoginPolling,
    pollLoginOnce,
    syncRuntimeStatusFromAccounts,
  };
}
