<template>
  <section class="panel accounts-panel">
    <div class="panel-head">
      <div>
        <h2>登录账户管理</h2>
        <p>{{ accountSummaryText }}</p>
      </div>
      <div class="toolbar">
        <el-button @click="$emit('create')">新增登录账户</el-button>
        <el-button :disabled="!selectedAccount" @click="$emit('edit', selectedAccount)">编辑选中账户</el-button>
        <el-button :disabled="!selectedAccount" type="danger" plain @click="$emit('delete', selectedAccount)">删除选中账户</el-button>
        <el-button :disabled="!selectedAccount || captureBusy" type="success" @click="$emit('capture', selectedAccount)">采集选中账号</el-button>
        <el-button :disabled="!selectedAccount" type="warning" plain @click="$emit('import-cookie', selectedAccount)">导入Cookie</el-button>
      </div>
    </div>

    <div class="account-filter-row">
      <span>平台筛选</span>
      <el-radio-group v-model="localFilter" size="small" @change="onFilterChange">
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
      @current-change="onSelectionChange"
    >
      <el-table-column label="平台" width="92">
        <template #default="{ row }">
          <el-tag effect="light">{{ platformLabel(row.platform) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="登录识别名" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ loginIdentityLabel(row) }}</template>
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
            <el-button size="small" type="warning" plain @click="$emit('import-cookie', row)">导入</el-button>
            <el-button size="small" type="success" plain :disabled="captureBusy" @click="$emit('capture', row)">采集</el-button>
            <el-button size="small" type="danger" plain @click="$emit('delete', row)">删除</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { ElMessageBox } from "element-plus/es/components/message-box/index.mjs";
import { platformLabel } from "../lib/platforms.js";
import {
  filterAccountsByPlatform,
  loginIdentityLabel,
  summarizeAccounts,
  selectedAccountVisible,
} from "../lib/accountMatrix.js";
import { accountResultText } from "../lib/platformOverview.js";

const props = defineProps({
  accounts: { type: Array, required: true },
  activePlatformFilter: { type: String, default: "all" },
  platformFilterOptions: { type: Array, required: true },
  captureBusy: { type: Boolean, default: false },
  selectedAccount: { type: Object, default: null },
});

const emit = defineEmits([
  "update:activePlatformFilter",
  "update:selectedAccount",
  "create",
  "edit",
  "delete",
  "capture",
  "import-cookie",
]);

const accountTableRef = ref(null);
const localFilter = ref(props.activePlatformFilter);

const filteredAccounts = computed(() =>
  filterAccountsByPlatform(props.accounts, props.activePlatformFilter),
);

const accountSummaryText = computed(() =>
  summarizeAccounts(props.accounts, props.activePlatformFilter),
);

watch(() => props.activePlatformFilter, (val) => {
  localFilter.value = val;
});

watch(() => [props.activePlatformFilter, filteredAccounts.value], () => {
  if (props.selectedAccount && !selectedAccountVisible(props.selectedAccount, props.activePlatformFilter)) {
    emit("update:selectedAccount", null);
    accountTableRef.value?.setCurrentRow?.(null);
  }
});

function onFilterChange(val) {
  emit("update:activePlatformFilter", val);
}

function onSelectionChange(row) {
  emit("update:selectedAccount", row);
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
  if (text === "上传失败" || text === "平台未配置客服账号" || text === "需要补充登录识别名") return "warning";
  if (text === "尚未采集" || text === "采集暂未接入") return "info";
  return "danger";
}

function accountResultDetail(account) {
  if (account?.lastCaptureSummary?.uploadMessage && !account.lastCaptureSummary.uploaded) {
    return account.lastCaptureSummary.uploadMessage;
  }
  return account?.lastError || account?.lastResult || "";
}

function showAccountResultDetail(account) {
  const detail = accountResultDetail(account);
  if (!detail) return;
  ElMessageBox.alert(detail, "最近结果详情", {
    confirmButtonText: "知道了",
  });
}

defineExpose({ accountTableRef });
</script>
