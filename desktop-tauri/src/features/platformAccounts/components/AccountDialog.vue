<template>
  <el-dialog v-model="account.visible" :title="account.id ? '编辑登录账户' : '新增登录账户'" width="520">
    <el-form label-position="top">
      <el-form-item label="平台">
        <el-select v-model="account.platform" class="full-input">
          <el-option v-for="item in accountPlatformOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="店铺名称">
        <el-input v-model="account.shopName" />
      </el-form-item>
      <el-form-item label="系统店铺ID">
        <el-input-number v-model="account.shopId" :min="0" :precision="0" class="full-input" />
      </el-form-item>
      <el-form-item label="账户备注">
        <el-input v-model="account.displayName" />
      </el-form-item>
      <el-form-item label="登录识别名">
        <el-input v-model="account.loginHint" />
      </el-form-item>
      <el-switch v-model="account.enabled" active-text="启用该账号参与一键采集" />
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
