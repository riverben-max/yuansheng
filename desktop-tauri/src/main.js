import { createApp } from "vue";
import { ElButton } from "element-plus/es/components/button/index.mjs";
import { ElDialog } from "element-plus/es/components/dialog/index.mjs";
import { ElForm, ElFormItem } from "element-plus/es/components/form/index.mjs";
import { ElInput } from "element-plus/es/components/input/index.mjs";
import { ElOption } from "element-plus/es/components/select/index.mjs";
import { ElRadioButton, ElRadioGroup } from "element-plus/es/components/radio/index.mjs";
import { ElSelect } from "element-plus/es/components/select/index.mjs";
import { ElSwitch } from "element-plus/es/components/switch/index.mjs";
import { ElTabPane, ElTabs } from "element-plus/es/components/tabs/index.mjs";
import { ElTable, ElTableColumn } from "element-plus/es/components/table/index.mjs";
import { ElTag } from "element-plus/es/components/tag/index.mjs";
import { ElTimePicker } from "element-plus/es/components/time-picker/index.mjs";
import { ElTooltip } from "element-plus/es/components/tooltip/index.mjs";
import "element-plus/theme-chalk/base.css";
import "element-plus/theme-chalk/el-button.css";
import "element-plus/theme-chalk/el-dialog.css";
import "element-plus/theme-chalk/el-form.css";
import "element-plus/theme-chalk/el-form-item.css";
import "element-plus/theme-chalk/el-input.css";
import "element-plus/theme-chalk/el-message.css";
import "element-plus/theme-chalk/el-message-box.css";
import "element-plus/theme-chalk/el-option.css";
import "element-plus/theme-chalk/el-overlay.css";
import "element-plus/theme-chalk/el-popper.css";
import "element-plus/theme-chalk/el-radio.css";
import "element-plus/theme-chalk/el-radio-button.css";
import "element-plus/theme-chalk/el-radio-group.css";
import "element-plus/theme-chalk/el-scrollbar.css";
import "element-plus/theme-chalk/el-select.css";
import "element-plus/theme-chalk/el-select-dropdown.css";
import "element-plus/theme-chalk/el-switch.css";
import "element-plus/theme-chalk/el-table.css";
import "element-plus/theme-chalk/el-table-column.css";
import "element-plus/theme-chalk/el-tabs.css";
import "element-plus/theme-chalk/el-tag.css";
import "element-plus/theme-chalk/el-time-picker.css";
import "element-plus/theme-chalk/el-tooltip.css";
import "./styles.css";
import App from "./App.vue";

const app = createApp(App);

[
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElOption,
  ElRadioButton,
  ElRadioGroup,
  ElSelect,
  ElSwitch,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElTabs,
  ElTag,
  ElTimePicker,
  ElTooltip,
].forEach((component) => {
  app.component(component.name, component);
});

app.config.errorHandler = (err, _instance, info) => {
  console.error("[vue error]", info, err);
};
if (typeof window !== "undefined") {
  window.addEventListener("unhandledrejection", (event) => {
    console.error("[unhandledrejection]", event.reason);
  });
}

app.mount("#app");
