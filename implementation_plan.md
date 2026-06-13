# Implementation Plan

[Overview]
Fix the Tauri v2 desktop application GitHub Actions build failures by correcting the Tauri schema configurations and permissions.

We will resolve the Tauri v2 schema and capability validation errors that caused the GitHub Actions workflows to fail on all three platforms (Windows, macOS, Linux). The issues stem from an invalid `"command"` property in `tauri.conf.json`'s sidecar plugin settings, and an invalid `"shell:allow-sidecar"` permission in `capabilities/default.json`. Correcting these configuration issues will allow Tauri to successfully validate the schema, resolve permissions, and compile flawless desktop installers.

[Types]
No changes are required in the project's data structures or domain types.

[Files]
We will modify the Tauri configuration and capabilities files to match the strict Tauri v2 schema.

Detailed breakdown:
- **Modified File:** `frontend/src-tauri/tauri.conf.json`
  - Remove the invalid `"command"` key from the `"ada-api"` sidecar configuration under `plugins -> shell -> sidecar`.
- **Modified File:** `frontend/src-tauri/capabilities/default.json`
  - Replace the invalid `"shell:allow-sidecar"` permission with the correct scoped `"shell:allow-ada-api"` permission.
- **Deleted File:** `get_github_logs.py`
  - Delete temporary investigative script.

[Functions]
No changes are needed to the Rust or Python functions.

[Classes]
No changes are needed to any classes.

[Dependencies]
No modifications are needed to packages or dependencies.

[Implementation Order]
We will apply targeted fixes sequentially to verify the configurations.

1. Update `frontend/src-tauri/tauri.conf.json` to match the exact Tauri v2 schema.
2. Update `frontend/src-tauri/capabilities/default.json` to reference the correct scoped sidecar permission `"shell:allow-ada-api"`.
3. Clean up the temporary `get_github_logs.py` file.
4. Commit changes to git and push to GitHub to trigger and verify the desktop compilation pipeline.

task_progress Items:
- [ ] Step 1: Update Tauri configuration schema in tauri.conf.json
- [ ] Step 2: Update default capability permissions in default.json
- [ ] Step 3: Clean up temporary get_github_logs.py script
- [ ] Step 4: Commit and push changes to trigger GitHub Actions build
