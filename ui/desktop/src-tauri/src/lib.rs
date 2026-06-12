use std::{
    io::{Read, Write},
    net::{TcpStream, ToSocketAddrs},
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};

use serde::Serialize;
use tauri::{Emitter, Manager, WebviewUrl, WebviewWindowBuilder, WindowEvent};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};
use tauri_plugin_shell::{process::CommandChild, ShellExt};
use windows_sys::Win32::UI::WindowsAndMessaging::GetForegroundWindow;

const API_HOST: &str = "127.0.0.1";
const API_PORT: u16 = 8765;
const HEALTH_PATH: &str = "/api/health";
const SIDECAR_NAME: &str = "ia-local-agent-api";
const MAIN_WINDOW_LABEL: &str = "main";
const OVERLAY_WINDOW_LABEL: &str = "overlay";

#[derive(Default)]
struct BackendProcess {
    child: Mutex<Option<CommandChild>>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum HealthState {
    Healthy,
    Unreachable,
    PortOccupied,
}

#[derive(Clone, Serialize)]
struct BackendLifecycleEvent {
    state: String,
    message: String,
}

#[derive(Clone, Serialize)]
struct OverlayContextEvent {
    handle: isize,
}

fn healthcheck() -> HealthState {
    let address = format!("{API_HOST}:{API_PORT}");
    let Ok(mut addresses) = address.to_socket_addrs() else {
        return HealthState::Unreachable;
    };
    let Some(address) = addresses.next() else {
        return HealthState::Unreachable;
    };
    let Ok(mut stream) = TcpStream::connect_timeout(&address, Duration::from_millis(450)) else {
        return HealthState::Unreachable;
    };

    let _ = stream.set_read_timeout(Some(Duration::from_millis(700)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(700)));

    let request = format!(
        "GET {HEALTH_PATH} HTTP/1.1\r\nHost: {API_HOST}:{API_PORT}\r\nConnection: close\r\n\r\n"
    );
    if stream.write_all(request.as_bytes()).is_err() {
        return HealthState::PortOccupied;
    }

    let mut response = String::new();
    if stream.read_to_string(&mut response).is_err() {
        return HealthState::PortOccupied;
    }

    if response.starts_with("HTTP/1.1 200") || response.starts_with("HTTP/1.0 200") {
        if response.contains("\"service\":\"ia-local-agent-api\"")
            || response.contains("\"service\": \"ia-local-agent-api\"")
        {
            return HealthState::Healthy;
        }
    }

    HealthState::PortOccupied
}

fn wait_for_backend(timeout: Duration) -> HealthState {
    let started = Instant::now();
    while started.elapsed() < timeout {
        match healthcheck() {
            HealthState::Healthy => return HealthState::Healthy,
            HealthState::PortOccupied => return HealthState::PortOccupied,
            HealthState::Unreachable => thread::sleep(Duration::from_millis(350)),
        }
    }
    HealthState::Unreachable
}

fn emit_backend_event(app: &tauri::AppHandle, state: &str, message: &str) {
    let _ = app.emit(
        "backend-lifecycle",
        BackendLifecycleEvent {
            state: state.to_string(),
            message: message.to_string(),
        },
    );
}

fn ensure_backend(app: tauri::AppHandle) {
    match healthcheck() {
        HealthState::Healthy => {
            emit_backend_event(&app, "ready", "Backend existente detectado en 127.0.0.1:8765");
            return;
        }
        HealthState::PortOccupied => {
            emit_backend_event(
                &app,
                "error",
                "El puerto 8765 esta ocupado por un proceso que no parece IA Local Agent.",
            );
            return;
        }
        HealthState::Unreachable => {}
    }

    emit_backend_event(&app, "starting", "Arrancando backend local...");

    let command = match app.shell().sidecar(SIDECAR_NAME) {
        Ok(command) => command
            .env("APP_ENV", "desktop")
            .env("API_HOST", API_HOST)
            .env("API_PORT", API_PORT.to_string())
            .env("LOCAL_API_KEY", "local-dev-token")
            .env(
                "API_ALLOWED_ORIGINS",
                "http://127.0.0.1:1420,http://localhost:1420,tauri://localhost,http://tauri.localhost",
            ),
        Err(error) => {
            emit_backend_event(&app, "error", &format!("No se encontro el sidecar: {error}"));
            return;
        }
    };

    let (mut receiver, child) = match command.spawn() {
        Ok(spawned) => spawned,
        Err(error) => {
            emit_backend_event(&app, "error", &format!("No se pudo arrancar el backend: {error}"));
            return;
        }
    };

    app.state::<BackendProcess>()
        .child
        .lock()
        .expect("backend process lock poisoned")
        .replace(child);

    thread::spawn(move || {
        while let Some(event) = receiver.blocking_recv() {
            eprintln!("backend sidecar: {event:?}");
        }
    });

    match wait_for_backend(Duration::from_secs(20)) {
        HealthState::Healthy => emit_backend_event(&app, "ready", "Backend local listo."),
        HealthState::PortOccupied => emit_backend_event(
            &app,
            "error",
            "El puerto 8765 cambio a un proceso no reconocido durante el arranque.",
        ),
        HealthState::Unreachable => emit_backend_event(
            &app,
            "error",
            "El backend no respondio a /api/health dentro del timeout.",
        ),
    }
}

fn shutdown_backend(app: &tauri::AppHandle) {
    let state = app.state::<BackendProcess>();
    let Some(child) = state
        .child
        .lock()
        .expect("backend process lock poisoned")
        .take()
    else {
        return;
    };

    if let Err(error) = child.kill() {
        eprintln!("failed to stop backend sidecar: {error}");
    }
}

fn ensure_overlay_window(app: &tauri::AppHandle) -> tauri::Result<()> {
    if app.get_webview_window(OVERLAY_WINDOW_LABEL).is_some() {
        return Ok(());
    }

    WebviewWindowBuilder::new(
        app,
        OVERLAY_WINDOW_LABEL,
        WebviewUrl::App("index.html?mode=overlay".into()),
    )
    .title("IA Local Agent Overlay")
    .inner_size(420.0, 560.0)
    .min_inner_size(360.0, 520.0)
    .resizable(true)
    .decorations(true)
    .always_on_top(true)
    .skip_taskbar(true)
    .visible(false)
    .build()?;

    Ok(())
}

fn toggle_overlay(app: &tauri::AppHandle) {
    if ensure_overlay_window(app).is_err() {
        return;
    }

    let Some(window) = app.get_webview_window(OVERLAY_WINDOW_LABEL) else {
        return;
    };

    match window.is_visible() {
        Ok(true) => {
            let _ = window.hide();
        }
        _ => {
            let _ = window.show();
            let _ = window.set_focus();
            let _ = window.set_always_on_top(true);
            let _ = window.emit("overlay-opened", ());
            let app = app.clone();
            thread::spawn(move || {
                thread::sleep(Duration::from_millis(60));
                refresh_overlay_context(app);
            });
        }
    }
}

fn refresh_overlay_context(app: tauri::AppHandle) {
    let Some(window) = app.get_webview_window(OVERLAY_WINDOW_LABEL) else {
        return;
    };
    let _ = window.hide();
    thread::sleep(Duration::from_millis(180));
    let foreground = unsafe { GetForegroundWindow() };
    let _ = window.show();
    let _ = window.set_focus();
    let _ = window.set_always_on_top(true);
    if !foreground.is_null() {
        let _ = window.emit("overlay-context", OverlayContextEvent { handle: foreground as isize });
    }
}

#[tauri::command]
fn refresh_overlay_context_command(app: tauri::AppHandle) {
    refresh_overlay_context(app);
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
/// Construye y ejecuta la aplicacion Tauri con los plugins necesarios para la UI desktop.
pub fn run() {
    let overlay_shortcut = Shortcut::new(Some(Modifiers::CONTROL | Modifiers::ALT), Code::Space);

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(move |app, shortcut, event| {
                    if shortcut == &overlay_shortcut && event.state() == ShortcutState::Pressed {
                        toggle_overlay(app);
                    }
                })
                .build(),
        )
        .setup(move |app| {
            app.manage(BackendProcess::default());
            ensure_overlay_window(app.handle())?;
            app.global_shortcut().register(overlay_shortcut)?;
            let handle = app.handle().clone();
            thread::spawn(move || ensure_backend(handle));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![refresh_overlay_context_command])
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                if window.label() == OVERLAY_WINDOW_LABEL {
                    api.prevent_close();
                    let _ = window.hide();
                    return;
                }
            }

            if window.label() == MAIN_WINDOW_LABEL && matches!(event, WindowEvent::CloseRequested { .. }) {
                shutdown_backend(window.app_handle());
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
