<template>
  <div class="panel settings-panel">
    <div class="panel-head compact">
      <div>
        <h2>运行设置</h2>
        <p>本机配置</p>
      </div>
      <el-button :loading="saving" type="primary" plain @click="$emit('save')">保存</el-button>
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
</template>

<script setup>
defineProps({
  settings: { type: Object, required: true },
  saving: { type: Boolean, default: false },
});

defineEmits(["save"]);
</script>
