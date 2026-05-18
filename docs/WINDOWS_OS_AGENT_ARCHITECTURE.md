# Windows OS Agent Architecture

## Vision

The Windows integration layer turns simple tools into an event-driven OS runtime. It stays offline, provider-agnostic and permission-first: LLM providers can request capabilities, but desktop state, automation and safety decisions live in local services.

## Folder Structure

```text
src/os_integration/
  models.py        Typed DTOs: windows, screenshots, OCR, workflows, hotkeys
  security.py      OS scopes, trust policy, app/title deny rules, confirmations
  events.py        Async EventBus, EventType, priorities, middleware
  windows.py       WindowManager, active window, monitor metadata, focus polling
  screenshots.py   ScreenshotService, cache, throttling, monitor/window/region capture
  ocr.py           OCRProvider abstraction, Tesseract provider, preprocessing
  hotkeys.py       HotkeyManager, dynamic bindings, keyboard backend
  automation.py    AutomationEngine, WorkflowExecutor, cancellation-ready steps
  lifecycle.py     WindowsIntegrationRuntime service composition
src/tools_catalog/windows_os.py
  Agent-facing tools for screen capture, OCR, active window and monitors
```

## Core Flows

```text
LLM/tool call
  -> ToolExecutor
  -> ToolPermissionPolicy
  -> windows_os tool
  -> OSSecurityPolicy
  -> service runtime
  -> JsonlAuditLog through ToolExecutor
```

```text
OS event source
  -> EventBus middleware
  -> priority queue
  -> subscribers
  -> workflows / UI / voice / memory
```

```text
Hotkey pressed
  -> HotkeyManager
  -> EventBus HOTKEY_PRESSED
  -> overlay / ask-current-window / push-to-talk workflow
```

## Screenshots

Supported targets:

- full virtual desktop
- monitor by index
- active window
- rectangular region

Recommended libraries:

- `mss`: fastest CPU capture, good multi-monitor support, simple API.
- `dxcam`: best future option for high-frequency capture and GPU-friendly loops, but Windows-only and heavier.
- `pyautogui`: convenient fallback, slower, less precise for multi-monitor/DPI.
- `Pillow ImageGrab`: simple fallback, acceptable for ad hoc captures.
- Win32 APIs: needed for window rectangles, DPI and special cases; capture of minimized windows is limited and often app-dependent.

Implementation notes:

- cache with short max age prevents repeated LLM/tool calls from hammering the compositor.
- rate limiting protects UI responsiveness.
- monitor coordinates use the Windows virtual screen, so left/top can be negative.
- DPI awareness should later be set at process startup with `SetProcessDpiAwarenessContext`.

## OCR

Provider model:

- `OCRProvider.recognize(image, language) -> OCRResult`
- `TesseractProvider`: CPU, mature, easy, good for clean UI text, weaker on small/anti-aliased text.
- `PaddleOCR`: stronger detection/recognition, GPU-capable, higher RAM/dependency cost.
- `EasyOCR`: easy setup and multi-language, heavier latency/RAM.
- Windows OCR APIs: native, good latency, but API wrapping and language pack availability complicate packaging.

Current MVP includes:

- provider abstraction
- Tesseract implementation when `pytesseract` is installed
- null provider with explicit metadata when no OCR backend exists
- grayscale, threshold and upscale preprocessing
- structured bounding boxes

## Window Context

`WindowManager` provides:

- active HWND
- title
- PID
- process name
- executable path
- rectangle
- monitor index
- normal/minimized/maximized/fullscreen state

Polling is used in the MVP because it is robust and dependency-light. Future hooks can use WinEvent hooks (`SetWinEventHook`) for lower latency focus changes.

## Event Bus

`EventBus` is async, bounded and priority-aware:

- `EventType` enumerates focus, session, power, battery, network, devices, clipboard, audio, process, monitors, idle, hotkeys and automation events.
- middleware can redact, debounce, drop or audit events.
- queue max size provides backpressure; dropped events are counted.
- subscriber failures are isolated.

Future event sources:

- WMI/Win32 power and device events
- `WM_CLIPBOARDUPDATE`
- process snapshots via `psutil`
- network status via Windows APIs
- idle time via `GetLastInputInfo`
- audio endpoints via CoreAudio wrappers

## Automation Runtime

`AutomationEngine` supports bounded steps:

- mouse move/click
- keyboard press/hotkey/type
- wait
- OCR condition (`ocr_contains`)

`WorkflowExecutor` runs ordered steps and stops on first failure. The design has room for rollback, visual wait conditions, image matching, window targeting and richer retry policies.

Real Windows limitations:

- UAC/admin windows cannot be safely automated from a non-elevated process.
- secure desktop, lock screen and credential dialogs are intentionally inaccessible.
- games/fullscreen/GPU surfaces may not expose UI Automation trees or capturable frames.
- minimized windows often cannot be captured unless the app paints off-screen.
- global keyboard hooks can require elevated privileges or be blocked by security tools.
- UI Automation is more reliable than coordinate clicks for standard desktop apps, but weaker for custom Electron/canvas/game UIs.

## Hotkeys

MVP uses optional `keyboard` backend:

- dynamic binding registry
- conflict replacement by binding name
- event publication
- policy-gated registration

Future production backend should prefer native low-level hooks for packaging control and clearer security behavior.

## Security Model

OS scopes:

- `screen.capture`
- `ocr.read`
- `window.inspect`
- `window.control`
- `keyboard.input`
- `mouse.input`
- `clipboard.read`
- `hotkey.register`
- `system_event.read`

Defaults:

- read/inspect scopes allowed
- keyboard, mouse, window control and clipboard read require confirmation
- password managers, credential titles, admin-like windows and secret/token titles are denied
- automation never bypasses UAC or secure desktop

Recommended production controls:

- per-app allowlists
- per-workflow approvals
- secure mode indicator
- human-in-the-loop for destructive workflows
- audit every requested target window and action
- never store screenshots/OCR text from sensitive windows

## Performance For i7-12700K + RTX 3060 Ti

Recommended defaults:

- event polling at 250-1000 ms depending on source
- screenshots on demand, not continuous
- OCR batch crops before full-screen OCR
- use PaddleOCR GPU only for explicit visual-analysis modes
- keep hotkey and event hooks lightweight
- isolate heavy OCR in worker threads/processes when UI arrives

Avoid:

- aggressive full-screen OCR loops
- high-FPS capture unless using `dxcam`
- blocking event subscribers
- storing unbounded screenshots
- GPU contention with games/editors

## MVP vs Future

MVP implemented now:

- service package and lifecycle manager
- screenshot service with mss/Pillow fallback
- OCR abstraction and Tesseract provider
- active window and monitor inspection
- focus-change polling through EventBus
- hotkey manager with optional backend
- automation engine skeleton with safe confirmation defaults
- tools: `capture_screenshot`, `ocr_screen`, `get_active_window`, `list_monitors`

Next iterations:

- native WinEvent hooks
- clipboard, power, battery, process and idle monitors
- UI Automation provider for semantic controls/buttons
- image matching and visual wait conditions
- overlay process/UI
- voice push-to-talk workflow
- workflow persistence and cancellation tokens across CLI/UI
- DXGI/dxcam capture provider
- encrypted screenshot/OCR cache or no-disk secure mode

## Recommended Dependencies

Base:

- `psutil`
- `pillow`
- `mss`
- `pywin32`
- `pyautogui`
- `keyboard`

OCR options:

- `pytesseract` plus local Tesseract binary
- `paddleocr` and CUDA runtime for advanced OCR
- `easyocr` for simpler multilingual experiments

Automation options:

- `pywinauto`
- `uiautomation`
- AutoHotkey for user-extensible macros, sandboxed behind confirmations

## Production Risks

- dependency packaging around OCR and Win32 hooks
- antivirus false positives for hooks/global hotkeys
- privacy leaks through screenshots/OCR logs
- DPI/multi-monitor coordinate drift
- localization issues in OCR and UI Automation labels
- Electron/browser custom controls requiring hybrid OCR/UIA strategies
- long-running monitors causing battery or latency regressions
