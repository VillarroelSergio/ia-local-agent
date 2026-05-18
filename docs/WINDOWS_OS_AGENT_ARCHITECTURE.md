# Windows Task Runtime Architecture

## Vision

`WindowsTaskManager` evolves the agent from primitive tools to semantic OS capabilities:

```text
user intent -> semantic capability -> workflow graph -> guarded Windows actions -> audit/events
```

The runtime is offline-first, provider-agnostic and security-first. LLM providers request capabilities; local services own planning constraints, permissions, execution, retries, cancellation and observability.

## Domain Structure

```text
src/windows/
  apps/          installed app discovery, app launch, workspace opening
  windows/       WindowManager, HWND, monitors, focus, move/resize/tile
  filesystem/    future downloads/project organization capabilities
  screen/        ScreenService, screenshots, region/window/monitor capture
  ocr/           OCRProvider, preprocessing, OCR results
  clipboard/     future clipboard read/write/events
  input/         keyboard/mouse backends hidden behind workflows
  automation/    AutomationEngine, low-level guarded step execution
  workflows/     WorkflowRunner, conditions, history, TaskScheduler
  events/        EventBus, publishers, subscribers, debounce/throttle
  permissions/   PermissionsManager, scopes, trust decisions
  policies/      allowlists, denylists, secure mode rules
```

Current implementation delegates to `src/os_integration/` for backwards compatibility while exposing the requested `src/windows/` domain facade.

## Runtime Lifecycle

```text
WindowsIntegrationRuntime.build()
  -> OSSecurityPolicy
  -> EventBus
  -> WindowManager
  -> ScreenshotService
  -> OCRService
  -> HotkeyManager
  -> AutomationEngine
  -> WorkflowRunner
  -> TaskScheduler
  -> ApplicationManager

start()
  -> event_bus.start()
  -> task_scheduler.start()
  -> focus monitor

stop()
  -> hotkeys.close()
  -> focus monitor stop
  -> task scheduler stop
  -> event bus stop
```

## Semantic Capabilities

Agent-facing tools should be capabilities, not raw input primitives:

- `focus_window`
- `summarize_active_window`
- `organize_windows`
- `open_project_workspace`
- `close_distraction_apps`
- `capture_and_analyze_screen`
- `move_window_to_monitor`
- `extract_visible_text`
- `automate_repetitive_task`

Raw primitives (`move_mouse`, `click_mouse`, `press_key`, `type_text`) remain for compatibility but should be treated as internal or last-resort actions.

## Execution Flow

```text
LLM tool call
  -> ToolExecutor
  -> ToolPermissionPolicy
  -> semantic tool
  -> OSSecurityPolicy window/scope check
  -> WorkflowRunner
  -> AutomationEngine / WindowManager / ScreenService / OCRService
  -> EventBus + audit log + ActionHistory
```

```text
OS event source
  -> publisher
  -> EventBus middleware
  -> bounded priority queue
  -> subscribers
  -> workflows / UI / memory / voice assistant
```

## WindowManager

Implemented:

- list visible windows
- active window
- focus by handle/query
- move/resize
- minimize/maximize/close request
- monitors
- fullscreen detection
- app/process detection
- basic tiling

Recommended stack:

- `ctypes` WinAPI: best minimal dependency for HWND, monitor, focus and move/resize.
- `pywin32`: better ergonomics and WinEvent hooks in production.
- `pywinauto`: good for classic Win32/UIA control trees and app automation.
- `uiautomation`: useful for semantic UI controls, accessibility tree and control names.
- `pygetwindow`: convenient but too limited as the core backend.

Edge cases:

- UAC/secure desktop cannot be automated safely.
- Minimized windows often cannot be captured.
- Electron, games and canvas UIs may not expose useful UI Automation trees.
- Multi-monitor coordinates use Windows virtual screen, so `left/top` can be negative.
- DPI scaling can drift coordinates unless the process sets DPI awareness at startup.
- Fullscreen/borderless apps may reject move/resize.

## Screen and OCR

Implemented:

- full virtual desktop screenshot
- monitor screenshot
- active-window screenshot
- region screenshot
- short-lived cache
- rate limiting
- optional compression
- OCR provider abstraction
- Tesseract provider with null fallback
- preprocessing: RGB, grayscale, threshold, upscale

Recommended stack:

- `mss`: default capture backend, fast and stable for multi-monitor.
- `Pillow`: fallback and preprocessing.
- `dxcam`: future high-frequency capture mode, useful for GPU-friendly loops.
- `pytesseract`: simple offline OCR, good MVP.
- `PaddleOCR`: stronger multilingual OCR and GPU option for RTX 3060 Ti, heavier packaging.
- `EasyOCR`: easy multilingual experiments, higher RAM/latency.

Default languages: use `eng`, `spa`, or `eng+spa` depending on Tesseract language packs.

## Workflow Runtime

Implemented:

- `AutomationStep`
- `AutomationWorkflow`
- `WorkflowRunner`
- `RetryPolicy`
- timeouts
- cancellation hook
- safe wait step
- OCR condition step
- window action steps
- screenshot step
- `ActionHistory`

Future workflow DSL:

```yaml
name: vscode_test_summary
steps:
  - action: focus_window
    args: { query: "Visual Studio Code" }
    retry_count: 2
  - action: hotkey
    args: { keys: ["ctrl", "`"] }
  - action: type
    args: { text: "pytest" }
  - action: press
    args: { key: "enter" }
  - action: ocr_contains
    args: { text: "failed" }
```

Future additions:

- rollback handlers
- visual wait conditions
- UI Automation selectors
- persisted workflow state
- per-step policy scopes
- workflow graph branches

## Events

Implemented:

- async bounded priority queue
- typed `EventType`
- subscribers and wildcard subscribers
- middleware
- debounce middleware
- throttle middleware
- focus-change publisher
- hotkey event publisher
- automation started/finished events

Future publishers:

- clipboard changes
- battery/power
- audio endpoints
- idle time
- monitor connection changes
- process start/stop
- network changes

Backpressure policy: bounded queue drops excess events and counts `dropped_events`. Heavy subscribers should spawn separate tasks or workers.

## Scheduler

Implemented:

- create task
- list tasks
- cancel task
- run task now
- recurring interval loop
- integration with WorkflowRunner and EventBus

Future:

- durable SQLite persistence
- cron expressions
- event-triggered tasks
- memory-aware triggers
- UI task monitor

## Security Model

Risk classes:

- `LOW`: read-only local state, system info, list windows.
- `MEDIUM`: screenshots, OCR, clipboard read, window focus.
- `HIGH`: keyboard/mouse input, window move/close, app launch, workflow execution.
- `CRITICAL`: admin actions, destructive filesystem, credential surfaces, dangerous PowerShell.

Defaults:

- screen/OCR/window inspection allowed.
- keyboard, mouse, clipboard read and window control require confirmation.
- destructive/admin tools are denied by tooling policy.
- credential managers, login/password titles, admin surfaces and secret/token windows are blocked.

The agent must not:

- read credentials or private keys
- access sensitive AppData/browser profile internals
- automate admin elevation
- control banking/login/password apps
- execute dangerous PowerShell
- type into password fields or credential dialogs

Production controls:

- per-app allowlists and denylists
- process policies
- filesystem policies
- secure mode indicator
- human confirmation for high-risk workflows
- no screenshot/OCR persistence for sensitive windows
- audit every capability request and effective target

## Performance

Target: Windows 11, i7-12700K, RTX 3060 Ti.

Recommended defaults:

- screenshots on demand, not continuous
- focus polling 250-1000 ms until WinEvent hooks are implemented
- crop before OCR
- batch OCR jobs
- use worker threads/processes for heavy OCR
- use `dxcam` only in explicit visual-analysis modes
- keep event subscribers non-blocking

Avoid:

- aggressive full-screen OCR loops
- high-FPS capture in normal assistant mode
- unbounded image cache
- long-running subscribers
- GPU contention with editors/games
- blocking calls inside the event loop

## Observability

Implemented:

- `ToolExecutor` JSONL audit
- workflow start/finish events
- `ActionHistoryEntry`
- per-step duration
- tool duration and errors

Future UI can render:

- current workflow
- action timeline
- executed tools
- durations
- failed step and error
- active policy decision
- screenshot/OCR provenance without exposing sensitive content

## UI Readiness

The runtime is ready for:

- Tauri desktop shell
- chat desktop
- overlay process
- screen overlay
- task monitor
- reasoning viewer
- voice assistant

UI should subscribe to EventBus and read workflow history rather than scraping logs.

## MVP Delivered

- `WindowManager` basic inspection and control
- `ScreenService` basic capture
- `OCRProvider` abstraction and Tesseract/null providers
- `EventBus`
- `WorkflowRunner`
- `PermissionsManager` / `OSSecurityPolicy`
- `TaskScheduler`
- semantic tools
- `src/windows/` domain facade
- initial tests

## Roadmap

1. Add native WinEvent hooks for focus/window/process changes.
2. Add clipboard, idle, battery, monitor and network publishers.
3. Add UI Automation selectors and semantic control actions.
4. Add durable workflow/task persistence.
5. Add visual planner with OCR/image matching conditions.
6. Add secure overlay confirmation UX.
7. Add PaddleOCR GPU mode for explicit analysis workflows.
8. Add Tauri task monitor and reasoning timeline.
9. Add per-workflow policy manifests.
10. Add encrypted/no-disk screenshot mode.

## Technical Risks

- OCR dependency packaging and language packs.
- Antivirus false positives for hooks/hotkeys/automation.
- Privacy leaks through screenshots/OCR/audit logs.
- DPI and multi-monitor coordinate drift.
- Electron/browser custom UI requiring hybrid OCR/UIA strategies.
- UAC/admin/secure desktop limitations.
- Long-running monitors causing CPU/battery regressions.
