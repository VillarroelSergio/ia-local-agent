#[cfg_attr(mobile, tauri::mobile_entry_point)]
/// Construye y ejecuta la aplicacion Tauri con los plugins necesarios para la UI desktop.
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
