// Prevents additional console window on Windows in release, do not remove!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri_plugin_shell::ShellExt;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // Spawn Python sidecar backend
            let app_handle = app.handle().clone();
            
            #[cfg(desktop)]
            {
                let sidecar = app.shell().sidecar("ada-api");
                match sidecar {
                    Ok(sidecar) => {
                        tauri::async_runtime::spawn(async move {
                            match sidecar.spawn() {
                                Ok((mut rx, mut tx)) => {
                                    println!("Successfully launched ada-api sidecar.");
                                    // Read stdout/stderr to prevent buffer overflow and keep sidecar logs
                                    while let Some(event) = rx.recv().clone().await {
                                        match event {
                                            tauri_plugin_shell::process::CommandEvent::Stdout(line) => {
                                                let log = String::from_utf8_lossy(&line);
                                                println!("[Sidecar Out]: {}", log.trim());
                                            }
                                            tauri_plugin_shell::process::CommandEvent::Stderr(line) => {
                                                let log = String::from_utf8_lossy(&line);
                                                eprintln!("[Sidecar Err]: {}", log.trim());
                                            }
                                            tauri_plugin_shell::process::CommandEvent::Terminated(status) => {
                                                eprintln!("[Sidecar]: Terminated with status {:?}", status);
                                                break;
                                            }
                                            _ => {}
                                        }
                                    }
                                }
                                Err(err) => {
                                    eprintln!("Failed to spawn ada-api sidecar: {}", err);
                                }
                            }
                        });
                    }
                    Err(err) => {
                        eprintln!("Failed to find ada-api sidecar: {}", err);
                    }
                }
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
