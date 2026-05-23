import test from "node:test";
import assert from "node:assert/strict";
import { ref } from "vue";

import { useAccounts } from "./useAccounts.js";

test("saveAccount preserves account metadata fields", async () => {
  const calls = [];
  const callSidecar = async (command, payload) => {
    calls.push({ command, payload });
    return { ok: true };
  };
  const refreshState = async () => {};
  const activePlatformFilter = ref("all");

  const { accountDialog, openAccountDialog, saveAccount } = useAccounts(callSidecar, refreshState, activePlatformFilter);
  openAccountDialog({
    id: "jd-1",
    platform: "jd",
    shopName: "京东菠萝店",
    shopId: 42,
    displayName: "菠萝客服",
    loginHint: "if自营菠萝",
    enabled: false,
  });
  accountDialog.shopName = "京东菠萝旗舰店";

  await saveAccount();

  assert.deepEqual(calls, [
    {
      command: "account_update",
      payload: {
        id: "jd-1",
        platform: "jd",
        shopName: "京东菠萝旗舰店",
        shopId: 42,
        displayName: "菠萝客服",
        loginHint: "if自营菠萝",
        enabled: false,
      },
    },
  ]);
});
