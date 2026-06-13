# Implementation Plan

[Overview]
Resolve the Tauri v2 desktop compilation error on GitHub Actions by migrating capability permissions to the standard scoped Tauri v2 structure.

We discovered the precise compilation error from the GitHub Actions logs. The error occurs because Tauri v2 does not generate or recognize dynamic permission names like `"shell:allow-ada-api"`. Instead, Tauri v2 relies on a strict capability model where sidecar commands are explicitly allowed using the built-in `"shell:allow-execute"` and `"shell:allow-spawn"` permissions, scoped specifically to the sidecar command name. We will update `capabilities/default.json` to define these scoped permissions and clean up temporary files to restore a pristine working tree.

[Types]
No changes are required in the project's data structures or domain types.

[Files]
We will modify the Tauri capabilities file to match standard Tauri v2 scoped rules, and clean up temporary scripts.

Detailed breakdown:
- **Modified File:** `frontend/src-tauri/capabilities/default.json`
  - Re-configure the capabilities to use `"shell:allow-execute"` and `"shell:allow-spawn"` with specific scopes for both `"binaries/ada-api"` and `"ada-api"` to satisfy all possible resolution patterns.
- **Deleted File:** `parse_jobs.py`
  - Delete temporary investigative script.
- **Deleted File:** `parse_check_runs.py`
  - Delete temporary investigative script.
- **Deleted File:** `run_jobs.json`
  - Delete temporary API file.
- **Deleted File:** `commit_check_runs.json`
  - Delete temporary API file.
- **Deleted Files:** `annotations_*.json`
  - Delete temporary annotations files.

[Functions]
No changes are needed to the Rust or Python functions.

[Classes]
No changes are needed to any classes.

[Dependencies]
No modifications are needed to packages or dependencies.

[Implementation Order]
We will apply targeted fixes sequentially to verify the configurations.

1. Update `frontend/src-tauri/capabilities/default.json` to define scoped permissions for `shell:allow-execute` and `shell:allow-spawn`.
2. Clean up temporary files: `parse_jobs.py`, `parse_check_runs.py`, `run_jobs.json`, `commit_check_runs.json`, and any generated `annotations_*.json` files.
3. Commit and push the updates to trigger and verify the GitHub Actions compilation.

task_progress Items:
- [ ] Step 1: Update default capability permissions with scoped sidecar rules in default.json
- [ ] Step 2: Clean up temporary helper files
- [ ] Step 3: Commit and push changes to trigger GitHub Actions build
