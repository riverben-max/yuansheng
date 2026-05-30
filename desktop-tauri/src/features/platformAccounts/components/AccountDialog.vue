<template>
  <el-dialog v-model="account.visible" :title="account.id ? '编辑登录账户' : '新增登录账户'" width="420">
    <el-form label-position="top">
      <el-form-item label="平台">
        <el-select v-model="account.platform" class="full-input">
          <el-option v-for="item in accountPlatformOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <!-- 新增时只显示平台 + 启用，其他字段在 Cookie 导入后自动识别填充。编辑时显示全部字段方便修改。 -->
      <template v-if="account.id">
        <el-form-item label="店铺名称">
          <el-input v-model="account.shopName" placeholder="用于上传展示和账号识别" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="account.displayName" placeholder="账号列表展示名称" />
        </el-form-item>
        <el-form-item label="登录识别名">
          <el-input v-model="account.loginHint" placeholder="多客服数据匹配用，如客服名、PIN 或 UID" />
        </el-form-item>
        <el-form-item label="后端店铺 ID">
          <el-input-number v-model="account.shopId" :min="0" class="full-input" controls-position="right" />
        </el-form-item>
      </template>
      <el-form-item v-else>
        <el-alert type="info" show-icon :closable="false">
          其他信息（店铺名、客服名、店铺 ID）会在导入 Cookie 时自动识别。如需修改，可在保存后再点“编辑”。
        </el-alert>
      </el-form-item>
      <el-form-item label="启用">
        <el-switch v-model="account.enabled" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="account.visible = false">取消</el-button>
      <el-button type="primary" @click="$emit('save')">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { platformList } from "../lib/platforms.js";

defineProps({
  account: { type: Object, required: true },
});

defineEmits(["save"]);

const accountPlatformOptions = platformList();
</script>
