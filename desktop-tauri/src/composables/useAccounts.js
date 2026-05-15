import { reactive, ref } from "vue";
import { ElMessageBox } from "element-plus/es/components/message-box/index.mjs";
import { normalizePlatform, platformLabel } from "../lib/platforms.js";
import { defaultPlatformForNewAccount } from "../lib/accountMatrix.js";

export function useAccounts(callSidecar, refreshState, activePlatformFilter) {
  const selectedAccount = ref(null);

  const accountDialog = reactive({
    visible: false,
    id: "",
    platform: "qn",
    shopName: "",
    displayName: "",
    loginHint: "",
    enabled: true,
  });

  function openAccountDialog(account = null) {
    const isEditing = Boolean(account?.id);
    Object.assign(accountDialog, {
      visible: true,
      id: account?.id || "",
      platform: isEditing
        ? normalizePlatform(account?.platform)
        : defaultPlatformForNewAccount(activePlatformFilter.value),
      shopName: account?.shopName || "",
      displayName: account?.displayName || "",
      loginHint: account?.loginHint || "",
      enabled: account?.enabled !== false,
    });
  }

  async function saveAccount() {
    const command = accountDialog.id ? "account_update" : "account_create";
    const payload = {
      id: accountDialog.id,
      platform: accountDialog.platform,
      shopName: accountDialog.shopName,
      displayName: accountDialog.displayName,
      loginHint: accountDialog.loginHint,
      enabled: accountDialog.enabled,
    };
    const result = await callSidecar(command, payload);
    if (result?.ok) {
      accountDialog.visible = false;
      await refreshState();
    }
  }

  async function deleteAccount(account) {
    const label = `${platformLabel(account.platform)} - ${account.displayName || account.shopName || account.id}`;
    await ElMessageBox.confirm(
      `删除登录账户"${label}"？\n\n该账户的登录凭证、采集记录将被永久删除。`,
      "删除确认",
      { confirmButtonText: "删除", cancelButtonText: "取消", type: "warning" },
    );
    let removeProfile = false;
    try {
      await ElMessageBox.confirm(
        "是否同时删除该账号的本地 Chrome 档案目录？\n\n删除后 Chrome 中保存的登录状态将被清除，下次需要重新扫码登录。",
        "清理本地档案",
        { confirmButtonText: "删除目录", cancelButtonText: "保留目录", type: "warning" },
      );
      removeProfile = true;
    } catch {
      // 用户选择保留目录
    }
    const result = await callSidecar("account_delete", { id: account.id, removeProfile });
    if (result?.ok) {
      // caller handles selectedAccount clearing
      await refreshState();
    }
  }

  return { accountDialog, selectedAccount, openAccountDialog, saveAccount, deleteAccount };
}
