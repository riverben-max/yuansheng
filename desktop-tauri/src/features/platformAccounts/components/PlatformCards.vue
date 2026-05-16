<template>
  <section class="platform-overview-grid">
    <article v-for="card in platformCards" :key="card.platform" class="platform-card">
      <div class="platform-card-head">
        <div>
          <span class="section-label">平台采集</span>
          <h2>{{ card.label }}</h2>
        </div>
        <el-tag :type="platformTagType(card.platform)" effect="light">{{ card.summaryText }}</el-tag>
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
          :type="platformTagType(card.platform)"
          :loading="captureBusy"
          :disabled="captureBusy || card.action.disabled"
          @click="$emit('capture-all', card.platform)"
        >
          {{ card.action.buttonText }}
        </el-button>
        <span v-if="card.action.hint">{{ card.action.hint }}</span>
      </div>
    </article>
  </section>
</template>

<script setup>
import { platformTagType } from "../lib/platforms.js";

defineProps({
  platformCards: { type: Array, required: true },
  captureBusy: { type: Boolean, default: false },
});

defineEmits(["capture-all"]);
</script>
