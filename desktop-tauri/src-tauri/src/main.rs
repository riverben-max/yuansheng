#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde_json::{json, Value};
use std::env;
use std::io::BufReader;
use std::io::Read;
use std::path::PathBuf;
use std::process::{Command, Stdio};
#[cfg(windows)]
use std::os::windows::process::CommandExt;
#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;
use std::time::Duration;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Emitter, Manager};

const DEFAULT_SIDECAR_TIMEOUT_SECS: u64 = 60;
const POLL_LOGIN_TIMEOUT_SECS: u64 = 20;
const START_LOGIN_TIMEOUT_SECS: u64 = 45;
const CAPTURE_TIMEOUT_SECS: u64 = 300;

#[tauri::command]
async fn sidecar_command(app: AppHandle, command: String, payload: Option<Value>) -> Result<Value, String> {
    tauri::async_runtime::spawn_blocking(move || sidecar_command_blocking(app, command, payload))
        .await
        .map_err(|error| format!("sidecar 后台任务异常：{error}"))?
}

#[tauri::command]
fn quit_app(app: AppHandle) {
    app.exit(0);
}

fn sidecar_command_blocking(app: AppHandle, command: String, payload: Option<Value>) -> Result<Value, String> {
    let payload_text = serde_json::to_string(&payload.unwrap_or_else(|| json!({})))
        .map_err(|error| format!("无法序列化 sidecar 参数：{error}"))?;

    let mut process = build_sidecar_process(&app, &command, &payload_text)?;
    let stdout = process
        .stdout
        .take()
        .ok_or_else(|| "无法读取 sidecar stdout。".to_string())?;
    let stderr = process
        .stderr
        .take()
        .ok_or_else(|| "无法读取 sidecar stderr。".to_string())?;

    // Read stdout and stderr concurrently on separate threads to avoid pipe deadlock.
    let stdout_handle =
        std::thread::Builder::new().name("sidecar-stdout".into()).spawn(move || read_pipe_bytes(stdout))
            .map_err(|error| format!("无法创建 stdout 读取线程：{error}"))?;
    let stderr_handle =
        std::thread::Builder::new().name("sidecar-stderr".into()).spawn(move || read_pipe_bytes(stderr))
            .map_err(|error| format!("无法创建 stderr 读取线程：{error}"))?;

    // Wait for process exit with timeout, polling so we can kill on timeout.
    let pid = process.id();
    let timeout_secs = sidecar_timeout_secs(&command);
    let deadline = std::time::Instant::now() + Duration::from_secs(timeout_secs);
    let status = loop {
        match process.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) => {
                if std::time::Instant::now() >= deadline {
                    // Try graceful shutdown first (without /F), then force kill.
                    let _ = Command::new("taskkill")
                        .args(["/T", "/PID", &pid.to_string()])
                        .stdout(Stdio::null())
                        .stderr(Stdio::null())
                        .spawn();
                    // Wait up to 3 seconds for graceful exit.
                    let grace_deadline = std::time::Instant::now() + Duration::from_secs(3);
                    let mut exited = false;
                    while std::time::Instant::now() < grace_deadline {
                        if process.try_wait().map(|s| s.is_some()).unwrap_or(false) {
                            exited = true;
                            break;
                        }
                        std::thread::sleep(Duration::from_millis(200));
                    }
                    if !exited {
                        let _ = Command::new("taskkill")
                            .args(["/F", "/T", "/PID", &pid.to_string()])
                            .stdout(Stdio::null())
                            .stderr(Stdio::null())
                            .spawn();
                        let _ = process.kill();
                        let _ = process.wait();
                    }
                    return Err(format!(
                        "sidecar 执行超时（{timeout_secs} 秒，PID={pid}），已终止。"
                    ));
                }
                std::thread::sleep(Duration::from_millis(100));
            }
            Err(error) => {
                return Err(format!("等待 sidecar 退出失败：{error}"));
            }
        }
    };

    let stdout_bytes = stdout_handle
        .join()
        .map_err(|_| "stdout 读取线程异常。".to_string())?
        .map_err(|error| format!("读取 sidecar 输出失败：{error}"))?;
    let stderr_bytes = stderr_handle
        .join()
        .map_err(|_| "stderr 读取线程异常。".to_string())?
        .map_err(|error| format!("读取 sidecar 错误输出失败：{error}"))?;

    let stdout_text = String::from_utf8_lossy(&stdout_bytes);
    let stderr_text = String::from_utf8_lossy(&stderr_bytes);

    let mut events: Vec<Value> = Vec::new();
    let mut final_response: Option<Value> = None;
    for line in stdout_text.lines() {
        if line.trim().is_empty() {
            continue;
        }
        let parsed: Value = serde_json::from_str(line).map_err(|error| {
            format!("sidecar 输出不是合法 JSON：{error}; line={}", sanitize_sensitive_text(line, 500))
        })?;
        if parsed.get("type").is_some() {
            let _ = app.emit("sidecar-event", parsed.clone());
            events.push(parsed);
        } else {
            final_response = Some(parsed);
        }
    }

    let mut response = final_response.unwrap_or_else(|| {
        if status.success() {
            json!({ "ok": true, "data": null })
        } else {
            let msg = sanitize_sensitive_text(stderr_text.trim(), 500);
            json!({ "ok": false, "message": if msg.is_empty() { "sidecar 异常退出，无错误输出。".to_string() } else { msg } })
        }
    });
    if let Some(object) = response.as_object_mut() {
        object.insert("events".to_string(), Value::Array(events));
    }
    Ok(response)
}

fn sidecar_timeout_secs(command: &str) -> u64 {
    match command {
        "poll_login" => POLL_LOGIN_TIMEOUT_SECS,
        "start_login" => START_LOGIN_TIMEOUT_SECS,
        "setup_browser_debug" => 30,
        "relaunch_browser_for_debug" => 30,
        "grab_browser_cookie" => 60,
        value if value.starts_with("capture_") => CAPTURE_TIMEOUT_SECS,
        _ => DEFAULT_SIDECAR_TIMEOUT_SECS,
    }
}

fn read_pipe_bytes<R: Read>(mut reader: R) -> Result<Vec<u8>, String> {
    let mut bytes = Vec::new();
    BufReader::new(&mut reader)
        .read_to_end(&mut bytes)
        .map_err(|error| format!("读取 pipe 失败：{error}"))?;
    Ok(bytes)
}

fn sanitize_sensitive_text(input: &str, limit: usize) -> String {
    let mut text = input.to_string();
    for marker in [
        "cookie",
        "set-cookie",
        "authorization",
        "csrf",
        "token",
        "secret",
        "x-sign",
        "sign",
        "thor",
        "pin",
        "pt_pin",
        "pass_id",
        "jsessionid",
        "windows_app_shop_token",
        "_m_h5_tk",
        "_tb_token_",
    ] {
        text = redact_marker_values(&text, marker);
    }
    if text.chars().count() > limit {
        let take = limit.saturating_sub(3);
        let mut truncated: String = text.chars().take(take).collect();
        truncated.push_str("...");
        return truncated;
    }
    text
}

fn redact_marker_values(input: &str, marker: &str) -> String {
    let lower = input.to_ascii_lowercase();
    let marker_lower = marker.to_ascii_lowercase();
    let bytes = input.as_bytes();
    let mut output = String::with_capacity(input.len());
    let mut cursor = 0;
    while let Some(relative) = lower[cursor..].find(&marker_lower) {
        let start = cursor + relative;
        let marker_end = start + marker.len();
        let search_end = (marker_end + 40).min(input.len());
        let delimiter = bytes[marker_end..search_end]
            .iter()
            .position(|byte| *byte == b':' || *byte == b'=');
        let Some(delimiter_offset) = delimiter else {
            output.push_str(&input[cursor..marker_end]);
            cursor = marker_end;
            continue;
        };

        let value_prefix_end = marker_end + delimiter_offset + 1;
        let mut value_start = value_prefix_end;
        while value_start < input.len() && matches!(bytes[value_start], b' ' | b'\t') {
            value_start += 1;
        }
        let quote = if value_start < input.len() && (bytes[value_start] == b'"' || bytes[value_start] == b'\'') {
            let quote = bytes[value_start];
            value_start += 1;
            Some(quote)
        } else {
            None
        };
        let mut value_end = value_start;
        while value_end < input.len() {
            let byte = bytes[value_end];
            if quote.map(|q| byte == q).unwrap_or(matches!(byte, b',' | b';' | b'}' | b' ' | b'\t' | b'\r' | b'\n')) {
                break;
            }
            value_end += 1;
        }

        output.push_str(&input[cursor..value_start]);
        output.push_str("<redacted>");
        cursor = value_end;
    }
    output.push_str(&input[cursor..]);
    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn poll_login_timeout_allows_slow_browser_attach() {
        assert_eq!(sidecar_timeout_secs("poll_login"), 20);
    }

    #[test]
    fn sanitize_sensitive_text_redacts_and_truncates_output() {
        let raw = r#"line={"cookie":"thor=secret-thor; pin=secret-pin","x-sign":"secret-sign","message":"bad"}"#;
        let sanitized = sanitize_sensitive_text(raw, 80);

        assert!(!sanitized.contains("secret-thor"));
        assert!(!sanitized.contains("secret-pin"));
        assert!(!sanitized.contains("secret-sign"));
        assert!(sanitized.len() <= 80);
    }
}

fn build_sidecar_process(
    app: &AppHandle,
    command: &str,
    payload_text: &str,
) -> Result<std::process::Child, String> {
    // 1. Explicit environment variable (production / manual override).
    if let Ok(exe) = env::var("YUANSHENG_SIDECAR_EXE") {
        return spawn_sidecar(Command::new(exe), command, payload_text);
    }

    // 2. Debug build: prefer Python script for fast iteration without rebuilding sidecar.exe.
    //    Set YUANSHENG_FORCE_BUNDLED_SIDECAR=1 to skip this and use the bundled exe instead.
    #[cfg(debug_assertions)]
    {
        if env::var("YUANSHENG_FORCE_BUNDLED_SIDECAR").is_err() {
            if let Ok(script) = dev_sidecar_script() {
                let mut last_err = String::new();
                for python_cmd in &["python3", "python", "py"] {
                    let mut cmd = Command::new(python_cmd);
                    cmd.arg(&script);
                    match spawn_sidecar(cmd, command, payload_text) {
                        Ok(child) => return Ok(child),
                        Err(e) => { last_err = e; }
                    }
                }
                eprintln!(
                    "[dev] Python sidecar 启动失败，回退到打包二进制。最近错误：{last_err}"
                );
            }
        }
    }

    // 3. Bundled sidecar next to the Tauri executable.
    if let Ok(exe_dir) = app
        .path()
        .resource_dir()
        .map(|p| p.join("binaries").join("yuansheng-sidecar.exe"))
    {
        if exe_dir.exists() {
            return spawn_sidecar(Command::new(exe_dir), command, payload_text);
        }
    }

    // 4. Release fallback: development Python script (e.g., when running unbundled).
    let script = dev_sidecar_script()?;
    let mut last_err = "".to_string();
    for python_cmd in &["python3", "python", "py"] {
        let mut cmd = Command::new(python_cmd);
        cmd.arg(&script);
        match spawn_sidecar(cmd, command, payload_text) {
            Ok(child) => return Ok(child),
            Err(e) => { last_err = e; }
        }
    }
    return Err(format!("未找到 Python 解释器（已尝试 python3, python, py），可设置 YUANSHENG_SIDECAR_EXE 环境变量指定 sidecar 路径。最近错误：{last_err}"));
}

fn spawn_sidecar(
    mut command_builder: Command,
    command: &str,
    payload_text: &str,
) -> Result<std::process::Child, String> {
    command_builder.env("PYTHONUTF8", "1");
    command_builder.env("PYTHONIOENCODING", "utf-8");
    #[cfg(windows)]
    command_builder.creation_flags(CREATE_NO_WINDOW);
    command_builder
        .arg(command)
        .arg(payload_text)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("启动 sidecar 失败：{error}"))
}

fn dev_sidecar_script() -> Result<PathBuf, String> {
    if let Ok(path) = env::var("YUANSHENG_SIDECAR_SCRIPT") {
        let script = PathBuf::from(&path);
        if script.exists() {
            return Ok(script);
        }
    }
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let script = manifest_dir
        .join("..")
        .join("..")
        .join("desktop-client")
        .join("sidecar_cli.py");
    script
        .canonicalize()
        .map_err(|error| format!("找不到 sidecar_cli.py，可设置 YUANSHENG_SIDECAR_SCRIPT 环境变量指定路径：{error}"))
}

fn check_leftover_processes(app: &AppHandle) {
    let candidates = &["yuansheng-sidecar.exe"];
    let mut found = Vec::new();
    for name in candidates {
        let output = Command::new("tasklist")
            .args(["/FI", &format!("IMAGENAME eq {name}"), "/NH", "/FO", "CSV"])
            .output();
        if let Ok(out) = output {
            let text = String::from_utf8_lossy(&out.stdout);
            if text.contains(name) {
                found.push(name.to_string());
            }
        }
    }
    if !found.is_empty() {
        let _ = app.emit(
            "sidecar-event",
            serde_json::json!({
                "type": "log",
                "message": format!("检测到残留进程：{}。建议通过任务管理器手动终止。", found.join("、"))
            }),
        );
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .setup(|app| {
            // 检测并提示残留的 sidecar / Chrome 僵尸进程
            check_leftover_processes(app.app_handle());

            let show = MenuItem::with_id(app, "show", "显示窗口", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "退出", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show, &quit])?;

            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().expect("无法加载应用图标").clone())
                .menu(&menu)
                .on_menu_event(|app, event| {
                    match event.id.as_ref() {
                        "show" => {
                            if let Some(window) = app.get_webview_window("main") {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                        "quit" => {
                            let _ = app.emit("tray-quit", ());
                            app.exit(0);
                        }
                        _ => {}
                    }
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                let _ = window.hide();
                api.prevent_close();
            }
        })
        .invoke_handler(tauri::generate_handler![sidecar_command, quit_app])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
