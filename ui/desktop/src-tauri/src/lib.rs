use std::{
    io::{Read, Write},
    net::{TcpStream, ToSocketAddrs},
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};

use serde::Serialize;
use tauri::{Emitter, Manager, WindowEvent};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

const API_HOST: &str = "127.0.0.1";
const API_PORT: u16 = 8765;
const HEALTH_PATH: &str = "/api/health";
const SIDECAR_NAME: &str = "ia-local-agent-api";

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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
/// Construye y ejecuta la aplicacion Tauri con los plugins necesarios para la UI desktop.
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            app.manage(BackendProcess::default());
            let handle = app.handle().clone();
            thread::spawn(move || ensure_backend(handle));
            Ok(())
        })
        .on_window_event(|window, event| {
            if matches!(event, WindowEvent::CloseRequested { .. }) {
                shutdown_backend(window.app_handle());
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
