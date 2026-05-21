<template>
  <main class="shell">
    <section class="topbar">
      <div class="brand">
        <div class="mark">远</div>
        <div>
          <h1>远盛数据助手</h1>
          <p>千牛客服绩效采集</p>
        </div>
      </div>
      <div class="top-status">
        <el-tag :type="displayedStatusType" effect="light" round>{{ displayedRuntimeStatus }}</el-tag>
        <span>下次计划：{{ scheduleText }}</span>
        <span>最近执行：{{ state.lastRunAt || "--" }}</span>
      </div>
    </section>

    <el-tabs v-model="activeTab" class="workspace-tabs">
      <el-tab-pane label="数据采集" name="capture">
        <PlatformCards
          :platformCards="platformCards"
          :captureBusy="captureBusy"
          @capture-all="onCaptureAll"
        />

        <section class="capture-grid">
          <div class="panel control-panel">
            <div class="panel-head">
              <div>
                <h2>采集控制台</h2>
                <p>{{ latestOverviewSubtitle }}</p>
              </div>
            </div>

            <div class="metrics">
              <div class="metric">
                <span>全平台登录</span>
                <strong>{{ loginAccountMetricText }}</strong>
              </div>
              <div class="metric">
                <span>服务端</span>
                <strong>{{ shortServerUrl }}</strong>
              </div>
              <div class="metric">
                <span>最近状态</span>
                <strong>{{ overviewStatusText }}</strong>
              </div>
            </div>

            <div class="capture-overview">
              <div class="overview-head">
                <div>
                  <span class="section-label">最近采集概览</span>
                  <strong>{{ overviewTitle }}</strong>
                </div>
                <el-tag :type="overviewTagType" effect="light">{{ overviewStatusText }}</el-tag>
              </div>
              <div class="overview-facts">
                <div>
                  <span>客服名</span>
                  <strong>{{ overviewCustomerName }}</strong>
                </div>
                <div>
                  <span>数据日期</span>
                  <strong>{{ overviewRecordDate }}</strong>
                </div>
                <div>
                  <span>上传状态</span>
                  <strong>{{ overviewUploadText }}</strong>
                </div>
              </div>
              <div v-if="overviewFailureText" class="overview-alert">
                <span>{{ overviewFailureText }}</span>
                <strong>{{ overviewNextAction }}</strong>
              </div>
              <div v-if="businessMetrics.length" class="business-metrics">
                <div v-for="item in businessMetrics" :key="item.key" class="business-metric">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </div>
              </div>
              <div v-else class="empty-overview">尚未采集</div>
            </div>

            <div class="actions">
              <el-button size="large" @click="refreshState">刷新状态</el-button>
            </div>
          </div>

          <SettingsPanel
            :settings="settings"
            :saving="saving"
            @save="saveSettings"
          />
        </section>

        <LogPanel
          :logs="logs"
          @clear="logs = []"
        />
      </el-tab-pane>

      <el-tab-pane label="用户管理" name="accounts">
        <AccountTable
          :accounts="accounts"
          :activePlatformFilter="activePlatformFilter"
          :platformFilterOptions="platformFilterOptions()"
          :loginBusy="loginBusy"
          :captureBusy="captureBusy"
          :selectedAccount="selectedAccount"
          @update:activePlatformFilter="activePlatformFilter = $event"
          @update:selectedAccount="selectedAccount = $event"
          @create="openAccountDialog()"
          @edit="openAccountDialog"
          @delete="onDeleteAccount"
          @login="onStartLogin"
          @capture="captureAccount"
          @import-cookie="onImportCookie"
        />
      </el-tab-pane>
    </el-tabs>

    <AccountDialog
      :account="accountDialog"
      @save="saveAccount"
    />
  </main>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { ElMessage } from "element-plus/es/components/message/index.mjs";
import { ElMessageBox } from "element-plus/es/components/message-box/index.mjs";
import { runSidecar, subscribeSidecarEvents } from "./lib/sidecar.js";
import { platformFilterOptions } from "./features/platformAccounts/lib/platforms.js";
import {
  buildPlatformSummaries,
  platformSummaryText,
  platformActionState,
  isAccountCaptureReady,
  accountResultText,
  uploadFailureText,
} from "./features/platformAccounts/lib/platformOverview.js";

import PlatformCards from "./features/platformAccounts/components/PlatformCards.vue";
import AccountTable from "./features/platformAccounts/components/AccountTable.vue";
import SettingsPanel from "./components/SettingsPanel.vue";
import AccountDialog from "./features/platformAccounts/components/AccountDialog.vue";
import LogPanel from "./components/LogPanel.vue";

import { useSettings } from "./composables/useSettings.js";
import { useLoginPolling } from "./features/platformAccounts/composables/useLoginPolling.js";
import { useCapture } from "./features/platformAccounts/composables/useCapture.js";
import { useAccounts } from "./features/platformAccounts/composables/useAccounts.js";

// ── App-level refs ──
const activeTab = ref("capture");
const logs = ref([]);
const activePlatformFilter = ref("all");

// ── callSidecar wrapper ──
async function callSidecar(command, payload = {}, options = {}) {
  try {
    const result = await runSidecar(command, payload);
    if (result.ok === false && !options.suppressError) {
      ElMessage.error(result.message || "操作失败");
    }
    return result;
  } catch (error) {
    if (!options.suppressError) ElMessage.error(String(error));
    return { ok: false, message: String(error) };
  }
}

// ── Composables ──
const { state, settings, accounts, saving, applyState, refreshState, saveSettings } = useSettings(callSidecar);
const { loginBusy, runtimeStatus, statusDanger,
        loginSummaryStatus,
        startLogin, stopLoginPolling,
        syncRuntimeStatusFromAccounts } = useLoginPolling(callSidecar, refreshState, accounts);
const { captureBusy, captureAll, captureAccount } = useCapture(callSidecar, refreshState, applyState);
const { accountDialog, selectedAccount, openAccountDialog, saveAccount, deleteAccount } =
  useAccounts(callSidecar, refreshState, activePlatformFilter);

// ── Computed ──
const enabledAccounts = computed(() => accounts.value.filter((a) => a.enabled));
const loggedInEnabledAccounts = computed(() => enabledAccounts.value.filter(isAccountCaptureReady));
const allEnabledAccountsLoggedIn = computed(
  () => enabledAccounts.value.length > 0 && loggedInEnabledAccounts.value.length === enabledAccounts.value.length,
);
const loginAccountMetricText = computed(() => `已登录 ${loggedInEnabledAccounts.value.length} / 启用 ${enabledAccounts.value.length}`);
const scheduleText = computed(() => (settings.scheduleEnabled ? `每日 ${settings.scheduleTime || "--"}` : "已关闭"));
const shortServerUrl = computed(() => (settings.serverUrl || "--").replace(/^https?:\/\//, ""));

const platformCards = computed(() =>
  buildPlatformSummaries(accounts.value).map((summary) => ({
    ...summary,
    summaryText: platformSummaryText(summary),
    action: platformActionState(summary),
  })),
);

const metricDefinitions = [
  { key: "consultationCount", label: "咨询人数" },
  { key: "receiveCount", label: "接待人数" },
  { key: "validReceiveCount", label: "有效接待人数" },
  { key: "inquiryCount", label: "询单人数" },
  { key: "conversionRate", label: "询单转化率", suffix: "%" },
  { key: "firstReplyTime", label: "首次响应", suffix: "秒" },
  { key: "avgReplyTime", label: "平均响应", suffix: "秒" },
  { key: "wwReplyRate", label: "旺旺回复率", suffix: "%" },
  { key: "satisfaction", label: "客户满意率", suffix: "%" },
];

const latestOverviewAccount = computed(() => {
  const candidates = accounts.value
    .filter((a) => a.lastCaptureSummary || a.lastFailureReason || a.lastError || a.lastResult)
    .map((a) => ({ account: a, time: Date.parse(accountEventTime(a)) || 0 }))
    .sort((left, right) => right.time - left.time);
  return candidates[0]?.account || null;
});

const latestCaptureSummary = computed(() => latestOverviewAccount.value?.lastCaptureSummary || null);

const latestOverviewSubtitle = computed(() => {
  if (latestCaptureSummary.value) {
    return `${latestCaptureSummary.value.subAccount || latestCaptureSummary.value.displayName || "--"}，${latestCaptureSummary.value.recordDate || "--"}`;
  }
  if (latestOverviewAccount.value && accountResultDetail(latestOverviewAccount.value)) return accountResultDetail(latestOverviewAccount.value);
  return "尚未采集";
});

const overviewStatusText = computed(() => {
  if (latestCaptureSummary.value) {
    return latestCaptureSummary.value.uploaded ? "采集成功" : uploadFailureText(latestCaptureSummary.value.uploadMessage);
  }
  if (latestOverviewAccount.value) return accountResultText(latestOverviewAccount.value);
  return "尚未采集";
});

const overviewTagType = computed(() => {
  if (latestCaptureSummary.value?.uploaded) return "success";
  if (latestCaptureSummary.value && !latestCaptureSummary.value.uploaded) return "warning";
  if (latestOverviewAccount.value) return accountResultTagType(latestOverviewAccount.value);
  return "info";
});

const overviewTitle = computed(() => {
  if (latestCaptureSummary.value) return latestCaptureSummary.value.capturedAt || "最近一次采集";
  if (latestOverviewAccount.value) return accountEventTime(latestOverviewAccount.value) || "最近一次采集";
  return "无采集记录";
});

const overviewCustomerName = computed(() => latestCaptureSummary.value?.subAccount || latestCaptureSummary.value?.displayName || "--");
const overviewRecordDate = computed(() => latestCaptureSummary.value?.recordDate || "--");

const overviewUploadText = computed(() => {
  if (!latestCaptureSummary.value) return "--";
  return latestCaptureSummary.value.uploaded ? "已上传" : latestCaptureSummary.value.uploadMessage || "未上传";
});

const overviewFailureText = computed(() => {
  if (latestCaptureSummary.value && !latestCaptureSummary.value.uploaded) return latestCaptureSummary.value.uploadMessage || "服务端上传失败";
  if (latestOverviewAccount.value && !latestCaptureSummary.value && !["采集成功", "尚未采集"].includes(overviewStatusText.value)) {
    return accountResultDetail(latestOverviewAccount.value);
  }
  return "";
});

const overviewNextAction = computed(() => {
  if (!overviewFailureText.value) return "";
  if (overviewStatusText.value === "需要重新登录") return "下一步：回到用户管理重新登录该账号";
  if (overviewStatusText.value === "平台未配置客服账号") return "下一步：在系统用户中创建对应客服账号";
  if (overviewStatusText.value === "上传失败") return "下一步：检查服务端地址或稍后重试";
  return "下一步：查看详情后重试采集";
});

const businessMetrics = computed(() => {
  const metrics = latestCaptureSummary.value?.metrics || {};
  return metricDefinitions
    .map((d) => ({ ...d, value: formatMetricValue(metrics[d.key], d.suffix) }))
    .filter((item) => item.value !== "--");
});

const displayedRuntimeStatus = computed(() => {
  if (isNeutralRuntimeStatus(runtimeStatus.value)) return loginSummaryStatus.value;
  return runtimeStatus.value;
});

const displayedStatusType = computed(() => {
  if (statusDanger.value) return "danger";
  if (displayedRuntimeStatus.value === "已全部登录") return "success";
  if (["采集中", "部分已登录", "等待登录", "等待扫码", "等待登录检测", "正在清理临时浏览器"].includes(displayedRuntimeStatus.value)) {
    return "warning";
  }
  if (["待登录", "请先登录", "登录超时", "登录窗口已关闭", "登录检测失败"].includes(displayedRuntimeStatus.value)) {
    return "danger";
  }
  return "info";
});

// ── Helpers ──
function isNeutralRuntimeStatus(status) {
  return ["待命", "已登录", "已全部登录", "部分已登录", "请先登录", "无启用账号"].includes(String(status || "").trim());
}

function formatMetricValue(value, suffix = "") {
  if (value === null || value === undefined || value === "") return "--";
  return `${value}${suffix || ""}`;
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

function accountResultTagType(account) {
  const text = accountResultText(account);
  if (text === "采集成功") return "success";
  if (text === "上传失败" || text === "平台未配置客服账号") return "warning";
  if (text === "尚未采集" || text === "采集暂未接入") return "info";
  return "danger";
}

// ── Event handlers ──
async function onCaptureAll(platform) {
  const result = await captureAll(platform, platformCards);
  if (result?.blocked) {
    activeTab.value = "accounts";
    ElMessage.warning(result.hint);
  }
}

async function onStartLogin(account) {
  await startLogin(account, activeTab);
}

async function onDeleteAccount(account) {
  await deleteAccount(account);
  selectedAccount.value = null;
}

async function onImportCookie(account) {
  if (!account) return;
  const platform = account.platform || "qn";
  const requestName = platform === "pdd" ? "csReportDetail"
    : platform === "douyin" ? "queryStaffData"
    : "queryStaffData";
  try {
    const { value } = await ElMessageBox.prompt(
      `操作步骤：\n1. 在浏览器中打开对应客服数据页面\n2. 按 F12 打开开发者工具 → Network 标签\n3. 刷新页面，找到 ${requestName} 请求\n4. 右键该请求 → Copy → Copy as cURL\n5. 粘贴到下方输入框`,
      "导入 Cookie",
      { inputType: "textarea", confirmButtonText: "导入", cancelButtonText: "取消" },
    );
    if (!value?.trim()) return;
    const result = await callSidecar("import_cookie", { accountId: account.id, cookieText: value.trim() });
    if (result?.ok) {
      ElMessage.success("Cookie 导入成功");
      if (result.data?.state) applyState(result.data.state);
    }
  } catch {
    // 用户取消
  }
}

// ── checkUpdate ──
async function checkUpdate() {
  const result = await callSidecar("check_update", {}, { suppressError: true });
  if (result?.ok && result.data?.updateAvailable) {
    ElMessage.success(
      `发现新版本 ${result.data.latestVersion}，当前版本 ${result.data.currentVersion}，请到发布渠道下载安装。`,
    );
  }
}

// ── Tauri lifecycle ──
let unlistenSidecar = null;
let unlistenTrayQuit = null;

onMounted(async () => {
  unlistenSidecar = await subscribeSidecarEvents(handleSidecarEvent);
  unlistenTrayQuit = await listen("tray-quit", handleTrayQuit);
  await refreshState();
  checkUpdate();
});

onUnmounted(() => {
  if (unlistenSidecar) unlistenSidecar();
  if (unlistenTrayQuit) unlistenTrayQuit();
  stopLoginPolling();
});

async function handleTrayQuit() {
  if (settings.exitRequiresConfirm) {
    try {
      await ElMessageBox.confirm("确定退出远盛数据助手？", "退出确认", {
        confirmButtonText: "退出",
        cancelButtonText: "取消",
        type: "warning",
      });
    } catch {
      return;
    }
  }
  await invoke("quit_app");
}

function handleSidecarEvent(event) {
  if (!event || typeof event !== "object") return;
  if (event.type === "log") {
    logs.value.push({
      time: event.time || new Date().toLocaleTimeString("zh-CN", { hour12: false }),
      message: event.message || "",
    });
    if (logs.value.length > 500) logs.value.shift();
    return;
  }
  if (event.type === "status") {
    runtimeStatus.value = event.status || runtimeStatus.value;
    statusDanger.value = Boolean(event.danger);
  }
}
</script>
