#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde_json::{json, Value};
use std::env;
use std::io::BufReader;
use std::io::Read;
use std::path::PathBuf;
use std::process::{Command, Stdio};
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
    let stdout_handle = std::thread::spawn(move || read_pipe_bytes(stdout));
    let stderr_handle = std::thread::spawn(move || read_pipe_bytes(stderr));

    // Wait for process exit with timeout, polling so we can kill on timeout.
    let pid = process.id();
    let timeout_secs = sidecar_timeout_secs(&command);
    let deadline = std::time::Instant::now() + Duration::from_secs(timeout_secs);
    let status = loop {
        match process.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) => {
                if std::time::Instant::now() >= deadline {
                    // Kill the entire process tree (sidecar + Chrome subprocess).
                    let _ = Command::new("taskkill")
                        .args(["/F", "/T", "/PID", &pid.to_string()])
                        .stdout(Stdio::null())
                        .stderr(Stdio::null())
                        .spawn();
                    let _ = process.kill();
                    let _ = process.wait();
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
            format!("sidecar 输出不是合法 JSON：{error}; line={line}")
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
            let msg = stderr_text.trim().to_string();
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn poll_login_timeout_allows_slow_browser_attach() {
        assert_eq!(sidecar_timeout_secs("poll_login"), 20);
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

    // 2. Bundled sidecar next to the Tauri executable.
    if let Ok(exe_dir) = app
        .path()
        .resource_dir()
        .map(|p| p.join("binaries").join("yuansheng-sidecar.exe"))
    {
        if exe_dir.exists() {
            return spawn_sidecar(Command::new(exe_dir), command, payload_text);
        }
    }

    // 3. Development: Python script relative to the Cargo manifest.
    let script = dev_sidecar_script()?;
    let mut python = Command::new("python");
    python.arg(script);
    spawn_sidecar(python, command, payload_text)
}

fn spawn_sidecar(
    mut command_builder: Command,
    command: &str,
    payload_text: &str,
) -> Result<std::process::Child, String> {
    command_builder.env("PYTHONUTF8", "1");
    command_builder.env("PYTHONIOENCODING", "utf-8");
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

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .setup(|app| {
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
