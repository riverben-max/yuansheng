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
        <section class="platform-overview-grid">
          <article v-for="card in platformCards" :key="card.platform" class="platform-card">
            <div class="platform-card-head">
              <div>
                <span class="section-label">平台采集</span>
                <h2>{{ card.label }}</h2>
              </div>
              <el-tag :type="card.platform === 'qn' ? 'success' : 'info'" effect="light">{{ card.summaryText }}</el-tag>
            </div>

            <div class="platform-stats">
              <div>
                <span>账号总数</span>
                <strong>{{ card.accountCount }}</strong>
              </div>
              <div>
                <span>启用账号</span>
                <strong>{{ card.enabledCount }}</strong>
              </div>
              <div>
                <span>已登录</span>
                <strong>{{ card.loggedInCount }}</strong>
              </div>
            </div>

            <div class="platform-latest">
              <div>
                <span>最近采集</span>
                <strong>{{ card.latestCaptureAt || "--" }}</strong>
              </div>
              <div>
                <span>最近结果</span>
                <strong>{{ card.latestResultText || "尚未采集" }}</strong>
              </div>
            </div>

            <div class="platform-action">
              <el-button
                :type="card.platform === 'qn' ? 'success' : 'info'"
                :loading="captureBusy"
                :disabled="captureBusy || card.action.disabled"
                @click="captureAll(card.platform)"
              >
                {{ card.action.buttonText }}
              </el-button>
              <span v-if="card.action.hint">{{ card.action.hint }}</span>
            </div>
          </article>
        </section>

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

          <div class="panel settings-panel">
            <div class="panel-head compact">
              <div>
                <h2>运行设置</h2>
                <p>本机配置</p>
              </div>
              <el-button :loading="saving" type="primary" plain @click="saveSettings">保存</el-button>
            </div>

            <el-form label-position="top" class="settings-form">
              <el-form-item label="每日执行时间">
                <el-time-picker
                  v-model="settings.scheduleTime"
                  format="HH:mm"
                  value-format="HH:mm"
                  :clearable="false"
                  class="full-input"
                />
              </el-form-item>
              <el-form-item label="服务端地址">
                <el-input v-model="settings.serverUrl" />
              </el-form-item>
              <div class="switch-list">
                <el-switch v-model="settings.scheduleEnabled" active-text="每日自动采集" />
                <el-switch v-model="settings.autoStartEnabled" active-text="登录 Windows 后自动启动" />
                <el-switch v-model="settings.exitRequiresConfirm" active-text="托盘退出二次确认" />
              </div>
            </el-form>
          </div>
        </section>

        <section class="panel log-panel">
          <div class="panel-head compact">
            <div>
              <h2>运行日志</h2>
              <p>{{ logs.length ? `${logs.length} 条` : "暂无日志" }}</p>
            </div>
            <el-button text @click="logs = []">清空</el-button>
          </div>
          <div class="terminal">
            <div v-if="!logs.length" class="empty-line">等待采集任务输出...</div>
            <div v-for="(log, index) in logs" :key="index" class="log-line">
              <span>[{{ log.time }}]</span>
              <p>{{ log.message }}</p>
            </div>
          </div>
        </section>
      </el-tab-pane>

      <el-tab-pane label="用户管理" name="accounts">
        <section class="panel accounts-panel">
          <div class="panel-head">
            <div>
              <h2>登录账户管理</h2>
              <p>{{ accountSummaryText }}</p>
            </div>
            <div class="toolbar">
              <el-button @click="openAccountDialog()">新增登录账户</el-button>
              <el-button :disabled="!selectedAccount" @click="openAccountDialog(selectedAccount)">编辑选中账户</el-button>
              <el-button :disabled="!selectedAccount" type="danger" plain @click="deleteSelectedAccount">删除选中账户</el-button>
              <el-button :disabled="!selectedAccount || loginBusy" @click="startLogin(selectedAccount)">登录/重新登录选中账户</el-button>
              <el-button :disabled="!selectedAccount || captureBusy" type="success" @click="captureSelectedAccount">采集选中账号</el-button>
            </div>
          </div>

          <div class="account-filter-row">
            <span>平台筛选</span>
            <el-radio-group v-model="activePlatformFilter" size="small">
              <el-radio-button v-for="item in platformFilterOptions" :key="item.value" :label="item.value">
                {{ item.label }}
              </el-radio-button>
            </el-radio-group>
          </div>

          <el-table
            ref="accountTableRef"
            :data="filteredAccounts"
            height="620"
            highlight-current-row
            class="account-table"
            @current-change="selectedAccount = $event"
          >
            <el-table-column label="平台" width="92">
              <template #default="{ row }">
                <el-tag effect="light">{{ platformLabel(row.platform) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="shopName" label="店铺名称" width="180" show-overflow-tooltip>
              <template #default="{ row }">{{ row.shopName || "--" }}</template>
            </el-table-column>
            <el-table-column prop="displayName" label="账户备注" width="140" show-overflow-tooltip />
            <el-table-column prop="loginHint" label="登录识别名" width="160" show-overflow-tooltip />
            <el-table-column prop="enabled" label="启用" width="72">
              <template #default="{ row }">
                <el-tag :type="row.enabled ? 'success' : 'info'" effect="light">{{ row.enabled ? "是" : "否" }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="Cookie状态" width="116">
              <template #default="{ row }">
                <el-tag :type="accountCookieStatusType(row)" effect="light">{{ accountCookieStatus(row) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="cookieUpdatedAt" label="最近登录" width="170" show-overflow-tooltip>
              <template #default="{ row }">{{ row.cookieUpdatedAt || "--" }}</template>
            </el-table-column>
            <el-table-column label="最近采集" width="170" show-overflow-tooltip>
              <template #default="{ row }">{{ accountLastCaptureAt(row) }}</template>
            </el-table-column>
            <el-table-column label="最近结果" min-width="180">
              <template #default="{ row }">
                <div class="result-cell">
                  <el-tag :type="accountResultTagType(row)" effect="light">{{ accountResultText(row) }}</el-tag>
                  <el-tooltip v-if="accountResultDetail(row)" :content="accountResultDetail(row)" placement="top">
                    <el-button link type="primary" @click="showAccountResultDetail(row)">详情</el-button>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="188" fixed="right">
              <template #default="{ row }">
                <div class="row-actions">
                  <el-button size="small" :disabled="loginBusy" @click="startLogin(row)">登录</el-button>
                  <el-button size="small" type="success" plain @click="captureAccount(row)">采集</el-button>
                  <el-button size="small" type="danger" plain @click="deleteAccount(row)">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="accountDialog.visible" :title="accountDialog.id ? '编辑登录账户' : '新增登录账户'" width="520">
      <el-form label-position="top">
        <el-form-item label="平台">
          <el-select v-model="accountDialog.platform" class="full-input">
            <el-option v-for="item in accountPlatformOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="店铺名称">
          <el-input v-model="accountDialog.shopName" />
        </el-form-item>
        <el-form-item label="账户备注">
          <el-input v-model="accountDialog.displayName" />
        </el-form-item>
        <el-form-item label="登录识别名">
          <el-input v-model="accountDialog.loginHint" />
        </el-form-item>
        <el-switch v-model="accountDialog.enabled" active-text="启用该账号参与一键采集" />
      </el-form>
      <template #footer>
        <el-button @click="accountDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="saveAccount">保存</el-button>
      </template>
    </el-dialog>
  </main>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { check } from "@tauri-apps/plugin-updater";
import { ElMessage } from "element-plus/es/components/message/index.mjs";
import { ElMessageBox } from "element-plus/es/components/message-box/index.mjs";
import {
  ACCOUNT_PLATFORM_OPTIONS,
  PLATFORM_FILTER_OPTIONS,
  defaultPlatformForNewAccount,
  enabledFilteredAccountCount as countEnabledFilteredAccounts,
  filterAccountsByPlatform,
  normalizePlatform,
  platformLabel,
  selectedAccountVisible,
  summarizeAccounts,
} from "./lib/accountMatrix";
import { accountResultText, buildPlatformSummaries, isAccountCaptureReady, platformActionState, platformSummaryText, uploadFailureText } from "./lib/platformOverview";
import { runSidecar, subscribeSidecarEvents } from "./lib/sidecar";
import {
  LOGIN_POLL_FIRST_DELAY_MS,
  LOGIN_POLL_INTERVAL_MS,
  LOGIN_POLL_REQUEST_TIMEOUT_MS,
  LOGIN_POLL_TIMEOUT_MS,
  loginPollFailureState,
} from "./lib/loginPollingPolicy";
import { captureMessageState } from "./lib/captureMessage";

const activeTab = ref("capture");
const captureBusy = ref(false);
const loginBusy = ref(false);
const saving = ref(false);
const runtimeStatus = ref("待命");
const statusDanger = ref(false);
const selectedAccount = ref(null);
const accountTableRef = ref(null);
const activePlatformFilter = ref("all");
const activeLoginAccountId = ref("");
const logs = ref([]);
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
const accountDialog = reactive({
  visible: false,
  id: "",
  platform: "qn",
  shopName: "",
  displayName: "",
  loginHint: "",
  enabled: true,
});
const accountPlatformOptions = ACCOUNT_PLATFORM_OPTIONS;
const platformFilterOptions = PLATFORM_FILTER_OPTIONS;
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

const enabledAccounts = computed(() => accounts.value.filter((account) => account.enabled));
const loggedInEnabledAccounts = computed(() => enabledAccounts.value.filter(isAccountCaptureReady));
const filteredAccounts = computed(() => filterAccountsByPlatform(accounts.value, activePlatformFilter.value));
const accountSummaryText = computed(() => summarizeAccounts(accounts.value, activePlatformFilter.value));
const enabledFilteredAccountCount = computed(() => countEnabledFilteredAccounts(accounts.value, activePlatformFilter.value));
const platformCards = computed(() =>
  buildPlatformSummaries(accounts.value).map((summary) => ({
    ...summary,
    summaryText: platformSummaryText(summary),
    action: platformActionState(summary),
  })),
);
const allEnabledAccountsLoggedIn = computed(
  () => enabledAccounts.value.length > 0 && loggedInEnabledAccounts.value.length === enabledAccounts.value.length,
);
const loginAccountMetricText = computed(() => `已登录 ${loggedInEnabledAccounts.value.length} / 启用 ${enabledAccounts.value.length}`);
const loginSummaryStatus = computed(() => {
  if (!enabledAccounts.value.length) return "无启用账号";
  if (allEnabledAccountsLoggedIn.value) return "已全部登录";
  if (loggedInEnabledAccounts.value.length > 0) return "部分已登录";
  return "待登录";
});
const scheduleText = computed(() => (settings.scheduleEnabled ? `每日 ${settings.scheduleTime || "--"}` : "已关闭"));
const shortServerUrl = computed(() => (settings.serverUrl || "--").replace(/^https?:\/\//, ""));
const latestOverviewAccount = computed(() => {
  const candidates = accounts.value
    .filter((account) => account.lastCaptureSummary || account.lastFailureReason || account.lastError || account.lastResult)
    .map((account) => ({ account, time: Date.parse(accountEventTime(account)) || 0 }))
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
    .map((definition) => ({
      ...definition,
      value: formatMetricValue(metrics[definition.key], definition.suffix),
    }))
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

let unlistenSidecar = null;
let unlistenTrayQuit = null;
let loginPollTimer = null;
let loginPollFirstTimer = null;
let loginPollStartedAt = 0;
let loginPollGeneration = 0;

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

watch([activePlatformFilter, filteredAccounts], () => {
  if (selectedAccount.value && !selectedAccountVisible(selectedAccount.value, activePlatformFilter.value)) {
    selectedAccount.value = null;
    accountTableRef.value?.setCurrentRow?.(null);
  }
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

async function checkUpdate() {
  try {
    const update = await check();
    if (!update) return;
    const { version, body } = update;
    try {
      await ElMessageBox.confirm(
        `发现新版本 v${version}${body ? `\n\n${body}` : ""}`,
        "软件更新",
        { confirmButtonText: "立即更新", cancelButtonText: "稍后", type: "info" },
      );
    } catch {
      return;
    }
    const loadingMessage = ElMessage({ message: `正在下载 v${version}...`, type: "info", duration: 0 });
    await update.downloadAndInstall(() => {
      // 下载完成后应用将自动重启安装
    });
    loadingMessage.close();
  } catch {
    // 更新检查失败（无端点配置或网络不可用）静默忽略
  }
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

async function startLogin(account = null) {
  if (loginBusy.value) return;
  if (!account?.id) {
    ElMessage.warning("请先在用户管理中选择一个登录账号");
    activeTab.value = "accounts";
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

function beginLoginPolling(accountId) {
  activeLoginAccountId.value = accountId;
  loginPollStartedAt = Date.now();
  const gen = ++loginPollGeneration;
  loginPollFirstTimer = window.setTimeout(() => {
    loginPollFirstTimer = null;
    if (loginPollGeneration !== gen) return;
    void pollLoginOnce(accountId, gen);
    loginPollTimer = window.setInterval(() => {
      if (loginPollGeneration !== gen) {
        window.clearInterval(loginPollTimer);
        loginPollTimer = null;
        return;
      }
      void pollLoginOnce(accountId, gen);
    }, LOGIN_POLL_INTERVAL_MS);
  }, LOGIN_POLL_FIRST_DELAY_MS);
}

function stopLoginPolling() {
  loginPollGeneration++;
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

async function pollLoginOnce(accountId, gen) {
  if (!accountId || accountId !== activeLoginAccountId.value || loginPollGeneration !== gen) return;
  if (Date.now() - loginPollStartedAt > LOGIN_POLL_TIMEOUT_MS) {
    stopLoginPolling();
    runtimeStatus.value = "登录超时";
    statusDanger.value = true;
    ElMessage.warning("登录等待超时，请重新点击该账号登录");
    return;
  }

  try {
    if (loginPollGeneration !== gen) return;
    const result = await withTimeout(
      callSidecar("poll_login", { accountId }, { suppressError: true }),
      LOGIN_POLL_REQUEST_TIMEOUT_MS,
      { ok: false, timeout: true, message: "登录检测超时，请重新点击该账号登录" },
    );
    if (loginPollGeneration !== gen) return;
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
    if (result.data?.state) applyState(result.data.state);
    if (result.data?.loggedIn) {
      stopLoginPolling();
      syncRuntimeStatusFromAccounts();
      statusDanger.value = false;
      ElMessage.success("登录成功，Cookie 已保存");
      return;
    }
    if (loginPollGeneration !== gen) return;
    const status = result.data?.status || "等待扫码";
    runtimeStatus.value = status;
    statusDanger.value = !["等待扫码", "等待登录检测", "正在清理临时浏览器"].includes(status);
    if (status === "登录窗口已关闭" || status === "登录检测失败") {
      stopLoginPolling();
      ElMessage.warning(result.data?.message || status);
    }
  } finally {
    // 代数校验替代了 loginPollRunning 布尔值
  }
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

async function captureAll(platform = "") {
  const action = platformCards.value.find((card) => card.platform === normalizePlatform(platform))?.action;
  if (action?.disabled) {
    activeTab.value = "accounts";
    ElMessage.warning(action.hint || "请先登录全部启用账号");
    return;
  }
  await runCapture("capture_all", {});
}

async function captureSelectedAccount() {
  if (!selectedAccount.value) return;
  await captureAccount(selectedAccount.value);
}

async function captureAccount(account) {
  await runCapture("capture_account", { accountId: account.id });
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

function openAccountDialog(account = null) {
  const isEditing = Boolean(account?.id);
  Object.assign(accountDialog, {
    visible: true,
    id: account?.id || "",
    platform: isEditing ? normalizePlatform(account?.platform) : defaultPlatformForNewAccount(activePlatformFilter.value),
    shopName: account?.shopName || "",
    displayName: account?.displayName || "",
    loginHint: account?.loginHint || "",
    enabled: account?.enabled !== false,
  });
}

function isNeutralRuntimeStatus(status) {
  return ["待命", "已登录", "已全部登录", "部分已登录", "请先登录", "无启用账号"].includes(String(status || "").trim());
}

function syncRuntimeStatusFromAccounts() {
  runtimeStatus.value = loginSummaryStatus.value;
  statusDanger.value = loginSummaryStatus.value === "待登录";
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

async function deleteSelectedAccount() {
  if (!selectedAccount.value) return;
  await deleteAccount(selectedAccount.value);
}

async function deleteAccount(account) {
  const label = `${platformLabel(account.platform)} - ${account.displayName || account.shopName || account.id}`;
  await ElMessageBox.confirm(`删除登录账户”${label}”？\n\n该账户的登录凭证、采集记录将被永久删除。`, “删除确认”, {
    confirmButtonText: “删除”,
    cancelButtonText: “取消”,
    type: “warning”,
  });
  let removeProfile = false;
  try {
    await ElMessageBox.confirm(
      `是否同时删除该账号的本地 Chrome 档案目录？\n\n删除后 Chrome 中保存的登录状态将被清除，下次需要重新扫码登录。`,
      “清理本地档案”,
      { confirmButtonText: “删除目录”, cancelButtonText: “保留目录”, type: “warning” },
    );
    removeProfile = true;
  } catch {
    // 用户选择保留目录
  }
  const result = await callSidecar(“account_delete”, { id: account.id, removeProfile });
  if (result?.ok) {
    selectedAccount.value = null;
    await refreshState();
  }
}

function showCaptureMessage(data = {}) {
  const messageState = captureMessageState(data);
  ElMessage[messageState.type](messageState.message);
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

function accountResultTagType(account) {
  const text = accountResultText(account);
  if (text === "采集成功") return "success";
  if (text === "上传失败" || text === "平台未配置客服账号") return "warning";
  if (text === "尚未采集" || text === "采集暂未接入") return "info";
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

function showAccountResultDetail(account) {
  const detail = accountResultDetail(account);
  if (!detail) return;
  ElMessageBox.alert(detail, "最近结果详情", {
    confirmButtonText: "知道了",
  });
}

function formatMetricValue(value, suffix = "") {
  if (value === null || value === undefined || value === "") return "--";
  return `${value}${suffix || ""}`;
}

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
