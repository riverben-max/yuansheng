import { ref, reactive } from "vue";
import { runSidecar } from "./sidecar";

export function useAccounts({ onStateUpdate }) {
  const accounts = ref([]);
  const selectedAccount = ref(null);

  const accountDialog = reactive({
    visible: false,
    id: "",
    displayName: "",
    loginHint: "",
    enabled: true,
  });

  function openAccountDialog(account = null) {
    Object.assign(accountDialog, {
      visible: true,
      id: account?.id || "",
      displayName: account?.displayName || "",
      loginHint: account?.loginHint || "",
      enabled: account?.enabled !== false,
    });
  }

  async function saveAccount() {
    const command = accountDialog.id ? "account_update" : "account_create";
    const payload = {
      id: accountDialog.id,
      displayName: accountDialog.displayName,
      loginHint: accountDialog.loginHint,
      enabled: accountDialog.enabled,
    };
    const result = await runSidecar(command, payload);
    if (result?.ok) {
      accountDialog.visible = false;
      if (result.data?.state) onStateUpdate(result.data.state);
      return true;
    }
    return false;
  }

  async function deleteAccount(account, { confirm, removeProfile }) {
    if (!(await confirm(`删除登录账户"${account.displayName || account.id}"？`, "删除确认"))) {
      return false;
    }
    const shouldRemoveProfile = await removeProfile();
    const result = await runSidecar("account_delete", {
      id: account.id,
      removeProfile: shouldRemoveProfile,
    });
    if (result?.ok) {
      selectedAccount.value = null;
      if (result.data?.state) onStateUpdate(result.data.state);
      return true;
    }
    return false;
  }

  async function deleteSelectedAccount({ confirm, removeProfile }) {
    if (!selectedAccount.value) return false;
    return deleteAccount(selectedAccount.value, { confirm, removeProfile });
  }

  function accountCookieStatus(account) {
    if (account?.cookieStatus) return account.cookieStatus;
    const status = String(account?.loginStatus || "").trim();
    if (account?.lastFailureReason === "需要重新登录" || status === "需要重新登录") return "需重新登录";
    if (status.includes("过期") || status.includes("失效")) return "已失效";
    if (account?.cookieUpdatedAt || account?.cookieSummary) return "已保存";
    return "未登录";
  }

  function accountCookieStatusType(account) {
    const status = accountCookieStatus(account);
    if (status === "已保存") return "success";
    if (status === "未登录") return "info";
    return "danger";
  }

  function accountLastCaptureAt(account) {
    return account?.lastCaptureSummary?.capturedAt || account?.lastCaptureAt || "--";
  }

  function accountResultText(account) {
    if (account?.lastCaptureSummary?.ok) {
      return account.lastCaptureSummary.uploaded ? "采集成功" : "上传失败";
    }
    const reason = String(account?.lastFailureReason || "").trim();
    if (reason) return reason;
    const status = String(account?.loginStatus || "").trim();
    if (status === "需要重新登录") return "需要重新登录";
    if (status === "采集失败") return "采集失败";
    if (account?.lastResult) return "采集成功";
    return "尚未采集";
  }

  function accountResultTagType(account) {
    const text = accountResultText(account);
    if (text === "采集成功") return "success";
    if (text === "上传失败") return "warning";
    if (text === "尚未采集") return "info";
    return "danger";
  }

  function accountResultDetail(account) {
    if (account?.lastCaptureSummary?.uploadMessage && !account.lastCaptureSummary.uploaded) {
      return account.lastCaptureSummary.uploadMessage;
    }
    return account?.lastError || account?.lastResult || "";
  }

  function accountEventTime(account) {
    return account?.lastFailureAt || account?.lastCaptureSummary?.capturedAt || account?.lastCaptureAt || "";
  }

  function isAccountCaptureReady(account) {
    return (
      account?.enabled &&
      (["已登录", "采集成功"].includes(String(account.loginStatus || "").trim()) ||
        accountCookieStatus(account) === "已保存")
    );
  }

  return {
    accounts,
    selectedAccount,
    accountDialog,
    openAccountDialog,
    saveAccount,
    deleteAccount,
    deleteSelectedAccount,
    accountCookieStatus,
    accountCookieStatusType,
    accountLastCaptureAt,
    accountResultText,
    accountResultTagType,
    accountResultDetail,
    accountEventTime,
    isAccountCaptureReady,
  };
}
