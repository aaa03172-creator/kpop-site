#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use tauri::Manager;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

struct SidecarState(Mutex<Option<CommandChild>>);

fn wait_for_health(timeout: Duration) -> Result<(), String> {
    let deadline = Instant::now() + timeout;
    let address: SocketAddr = "127.0.0.1:8765"
        .parse()
        .map_err(|error| format!("Invalid MouseDB address: {error}"))?;

    while Instant::now() < deadline {
        if let Ok(mut stream) = TcpStream::connect_timeout(&address, Duration::from_millis(500)) {
            let request = b"GET /api/health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n";
            if stream.write_all(request).is_ok() {
                let mut response = String::new();
                if stream.read_to_string(&mut response).is_ok() && response.contains("200 OK") {
                    return Ok(());
                }
            }
        }
        thread::sleep(Duration::from_millis(250));
    }

    Err("MouseDB sidecar did not become healthy at /api/health within 30 seconds.".to_string())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(SidecarState(Mutex::new(None)))
        .setup(|app| {
            let app_home = app.path().app_data_dir()?;
            let data_dir = app_home.join("data");
            let artifact_root = app_home.join("mousedb_artifacts");

            let args = vec![
                "--host".to_string(),
                "127.0.0.1".to_string(),
                "--port".to_string(),
                "8765".to_string(),
                "--data-dir".to_string(),
                data_dir.to_string_lossy().to_string(),
                "--artifact-root".to_string(),
                artifact_root.to_string_lossy().to_string(),
            ];

            let sidecar_command = app.shell().sidecar("mousedb-server")?.args(args);
            let (mut rx, child) = sidecar_command.spawn()?;
            *app.state::<SidecarState>().0.lock().expect("sidecar lock poisoned") = Some(child);

            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            println!("[mousedb-server] {}", String::from_utf8_lossy(&line));
                        }
                        CommandEvent::Stderr(line) => {
                            eprintln!("[mousedb-server] {}", String::from_utf8_lossy(&line));
                        }
                        _ => {}
                    }
                }
            });

            wait_for_health(Duration::from_secs(30)).map_err(Into::into)
        })
        .run(tauri::generate_context!())
        .expect("error while running MouseDB desktop app");
}
