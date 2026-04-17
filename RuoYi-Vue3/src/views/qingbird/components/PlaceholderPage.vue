<template>
  <div class="qb-placeholder-page">
    <div class="placeholder-icon">{{ icon }}</div>
    <h3>{{ title }}</h3>
    <p>该功能模块正在建设中，敬请期待...</p>
  </div>
</template>

<script setup>
defineProps({
  icon: { type: String, default: '🚀' },
  title: { type: String, default: '功能建设中' }
})
</script>

<style lang="scss" scoped>
.qb-placeholder-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 65vh;
  color: #aaa;
  text-align: center;

  .placeholder-icon {
    font-size: 72px;
    margin-bottom: 20px;
    opacity: 0.4;
  }

  h3 {
    font-size: 20px;
    color: #888;
    margin-bottom: 8px;
    font-weight: 600;
  }

  p {
    font-size: 14px;
  }
}
</style>
