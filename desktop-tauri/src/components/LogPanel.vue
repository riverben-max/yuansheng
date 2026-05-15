<template>
  <section class="panel log-panel">
    <div class="panel-head compact">
      <div>
        <h2>运行日志</h2>
        <p>{{ logs.length ? `${logs.length} 条` : "暂无日志" }}</p>
      </div>
      <el-button text @click="$emit('clear')">清空</el-button>
    </div>
    <div class="terminal">
      <div v-if="!logs.length" class="empty-line">等待采集任务输出...</div>
      <div v-for="(log, index) in logs" :key="index" class="log-line">
        <span>[{{ log.time }}]</span>
        <p>{{ log.message }}</p>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  logs: { type: Array, required: true },
});

defineEmits(["clear"]);
</script>
