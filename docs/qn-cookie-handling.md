# 千牛「从浏览器导入 Cookie」处理逻辑

> 1.1.8+ 版本起，千牛 cookie 的抓取和校验有一套**特殊处理逻辑**，避免直接保存
> 不完整的 cookie 误导客户。修改这块代码前请先读这份文档。

## 1. 为什么千牛 cookie 不能简单抓了就用

千牛后台 H5 接口（`mtop.alibaba.sycm.*` 等）调用时必须带下面两类字段，
缺一不可：

| 类别 | 字段（任一即可） | 来源页面 |
|---|---|---|
| **API 签名 token** | `_m_h5_tk` | `myseller.taobao.com` 主页加载时由 mtop 接口颁发 |
| **用户身份** | `unb` / `sn` / `tracknick` / `_nk_` | 登录成功后由 `*.taobao.com` 颁发 |

注意：
- `_tb_token_` 是 CSRF token，**不是**用户身份字段，**不能**作为完整性依据。
- `cookie2` 是会话标识，单独存在不足以让接口认账。
- 客户**只在登录页（loginmyseller）**点击登录后，浏览器停留在跳转中转页时，
  上面那些字段往往**还没全颁发**，cookie 长度通常 1500~2500 字节。
  完整 cookie 长度通常 4K+。

如果直接保存这种"半成品 cookie"，桌面端会显示「已保存」，但客户实际点采集
时接口会返回 `FAIL_SYS_SESSION_EXPIRED`，造成"明明刚登录怎么就过期"的困惑。

## 2. 处理流程（`sidecar_cli.py::grab_browser_cookie` 千牛分支）

```
点「浏览器」按钮
   │
   ▼
通过 CDP 抓 cookie（PLATFORM_COOKIE_DOMAINS["qn"] 域名过滤）
   │
   ▼
诊断日志：[千牛 cookie 诊断 首次抓取] ...关键字段...
   │
   ├── _m_h5_tk + (unb/sn/tracknick/_nk_ 任一) 都有 → 完整，正常保存
   │
   └── 缺关键字段 → 不完整
           │
           ▼
       通过 CDP 在已运行的 360 里新开标签页跳转 myseller 工作台
       https://myseller.taobao.com/home.htm/QnworkbenchHome/
           │
           ▼
       sleep 5 秒（让 myseller 首页加载并触发 mtop → 颁发 _m_h5_tk + 用户字段）
           │
           ▼
       重抓 cookie，再次诊断 [千牛 cookie 诊断 重抓后]
           │
           ├── 完整 → 保存
           │
           └── 仍不完整 → 不保存，再次自动开 myseller 工作台
                          返回 cookieSaved=false + loginPageOpened=true
                          前端弹对话框：「千牛登录信息不完整。已为你打开
                          工作台首页，请在浏览器里完成登录后，再点
                          「浏览器」按钮。」
```

## 3. 关键代码位置

| 功能 | 文件 | 关键标识 |
|---|---|---|
| 千牛 cookie 完整性判断 | `desktop-client/sidecar_cli.py` | `_qn_cookie_complete` 内嵌函数 |
| 千牛 cookie 诊断日志 | `desktop-client/sidecar_cli.py` | `_log_qn_cookie_fields` 内嵌函数 |
| 千牛重抓流程 | `desktop-client/sidecar_cli.py::grab_browser_cookie` | `if platform == "qn":` 分支 |
| 在已开浏览器里新开标签 | `desktop-client/browser_debug_setup.py` | `open_url_in_existing_browser` |
| 千牛工作台 URL | `desktop-client/browser_debug_setup.py` | `PLATFORM_LOGIN_URLS["qn"]` |
| 直采层 cookie 校验 | `desktop-client/direct_api_capture.py` | `_load_account_cookie` |

> **不要随便删 `sidecar_cli.py::grab_browser_cookie` 里 `if platform == "qn":` 这段。**
> 删掉客户就会重新踩"cookie 已保存但采集失败"的坑。

## 4. 用户标识字段为什么是这几个

| 字段 | 意义 |
|---|---|
| `unb` | 淘宝用户编号（数字 ID），最稳定 |
| `sn` | URL-encoded 中文昵称（"林志玲" 等），用作识别名最友好 |
| `tracknick` | URL-encoded 跟踪昵称 |
| `_nk_` | 登录账号别名 |

`_resolve_qn_identity_from_cookie`（`sidecar_cli.py`）按 sn / _nk_ / tracknick / lgc
优先级取识别名，且**跳过 `tb<纯数字>` 这种内部分配 ID**。

## 5. 改完 Python 代码怎么让 dev 模式生效

`npm run tauri:dev` 启动后，每次桌面端调用 sidecar 命令时：

```
main.rs::build_sidecar_process 的优先级：
  1. 环境变量 YUANSHENG_SIDECAR_EXE 指定的 exe（生产/手动覆盖）
  2. debug 构建：spawn `python sidecar_cli.py`（理论上，每次重新加载脚本）
  3. 找 src-tauri/binaries/yuansheng-sidecar.exe（打包好的二进制）
  4. release fallback：再试 python 脚本
```

**踩过的坑（2026-05-31）**：
- dev 模式按理说优先 python 脚本，每次调用都加载最新代码。
- 但实际经验里有时还是会用到 `yuansheng-sidecar.exe`（系统 PATH 不对、
  或 python 版本被屏蔽等），而那个 exe 是**预打包**的旧版。
- 表现：你改了 `sidecar_cli.py`，重启 dev 后依然是旧逻辑。

**最稳妥的做法**：改完 Python 代码后，**重新打包 sidecar.exe**：

```powershell
cd D:\Tools\work_project\yuansheng-push\desktop-tauri
pwsh -ExecutionPolicy Bypass -File scripts\build_sidecar.ps1
```

打包大约 1~2 分钟，结束后 `src-tauri\binaries\yuansheng-sidecar.exe`
会被覆盖成最新版。无论 dev 模式选 python 脚本还是回退到 exe，都是新代码。

然后**彻底重启 dev**（Ctrl+C → `npm run tauri:dev`）。

> 如果 Ctrl+C 之后还有残留 yuansheng-data-assistant.exe 占用，
> 可能是上一次 dev 的崩溃残留。手动 taskkill /F /PID <pid> 即可。

## 6. 调试日志怎么看

千牛 grab cookie 流程现在会输出诊断日志，格式：

```
[千牛 cookie 诊断 首次抓取] 长度 2081，字段数 25，关键字段：_m_h5_tk=有, sn=无,
unb=无, _tb_token_=有, tracknick=无, _nk_=无, lgc=无, cookie2=有
```

在桌面端「数据采集」页 / 用户管理页都有运行日志窗口。如果客户反馈千牛
导入失败，先让客户把这条诊断日志的内容截图发回来，立刻就能定位是哪个
字段缺。

## 7. 常见诊断结果对照

| 诊断输出 | 含义 | 处理 |
|---|---|---|
| `_m_h5_tk=无` | 客户没访问过 myseller 主页 | 自动跳工作台重抓即可 |
| `unb=无, sn=无, tracknick=无, _nk_=无` | 客户未真正登录或登录态没颁发 | 自动跳工作台 + 提示客户继续登录 |
| 全部=有 + 长度 4K+ | 完整 | 直接保存 |
| 长度 1500~2500 + 关键字段缺 | 半成品 cookie | 走重抓流程 |
