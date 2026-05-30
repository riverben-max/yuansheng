# AGENTS.md

本仓库是远盛项目正式 Git 仓库。

## 路径约定

- 仓库根目录：`D:\Tools\work_project\yuansheng-push`
- 远程仓库：`git@github.com:riverben-max/yuansheng.git`
- 默认分支：`main`
- 桌面端 Tauri：`desktop-tauri`
- 桌面端采集核心：`desktop-client`
- 管理后台前端：`RuoYi-Vue3`

## 工作约定

- 修改远盛代码、查看 Git 状态、提交、测试、构建时，以本仓库根目录为准。
- 不要误改外层副本 `D:\Tools\work_project\desktop-tauri` 或 `D:\Tools\work_project\desktop-client`。
- 所有文件使用 UTF-8 无 BOM；包含中文的文件保持 LF 换行。
- 后端由用户在 IntelliJ IDEA 中用 JDK 17 运行；不要自行启动或重启后端服务。
- 桌面端发版（升版本号、打包、生成 update.json、上传服务器）按 [`docs/release-process.md`](docs/release-process.md) 执行。

## 桌面端前端结构约束

- `desktop-tauri/src` 根目录只保留入口级文件，例如 `App.vue`、`main.js`、全局样式和少量启动配置。
- 纯 JS 工具、状态计算、sidecar 通信、轮询策略等放在 `desktop-tauri/src/lib/`，测试文件尽量与对应模块放在同一目录。
- 页面级 Vue 组件后续放在 `desktop-tauri/src/views/`，不要继续把完整页面堆进 `App.vue`。
- 可复用 UI 组件后续放在 `desktop-tauri/src/components/`，例如平台卡片、账号表格、运行日志、设置面板、弹窗。
- 平台差异和平台定义后续放在 `desktop-tauri/src/platforms/`；新增平台不要直接把平台专属判断散落到 `App.vue`。
- 结构整理应分步提交，每一步都要保持 `npm run build` 和对应前端测试可通过。
