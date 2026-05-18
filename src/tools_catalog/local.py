"""Tools locales Windows/filesystem/clipboard/browser/PowerShell."""

from __future__ import annotations

import platform
import subprocess
import webbrowser
from ctypes import Structure, byref, c_long, windll
from pathlib import Path

import psutil

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import pyperclip
except ImportError:
    pyperclip = None

try:
    from tooling import RiskLevel, ToolContext, ToolDefinition, ToolMetadata
except ModuleNotFoundError:
    from src.tooling import RiskLevel, ToolContext, ToolDefinition, ToolMetadata

from .schemas import (
    ClickMouseInput,
    DirectoryListInput,
    EmptyInput,
    HotkeyInput,
    LimitInput,
    MoveMouseInput,
    OpenApplicationInput,
    OpenUrlInput,
    PowerShellInput,
    PressKeyInput,
    ReadTextFileInput,
    SearchFilesInput,
    SetClipboardInput,
    TypeTextInput,
)


MAX_PROCESS_LIMIT = 50
MAX_SEARCH_LIMIT = 100
MAX_DIRECTORY_LIMIT = 100
MAX_FILE_READ_CHARS = 12000
MAX_CLIPBOARD_CHARS = 8000
MAX_POWERSHELL_TIMEOUT = 15
MAX_MOUSE_COORDINATE = 10000
EXCLUDED_SEARCH_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "data",
}

ALLOWED_POWERSHELL_COMMANDS = {
    "get-date",
    "get-process",
    "get-service",
    "get-computerinfo",
    "get-childitem",
    "get-content",
    "test-path",
    "where-object",
    "select-object",
    "sort-object",
    "measure-object",
    "format-table",
    "format-list",
}

BLOCKED_POWERSHELL_TOKENS = [";", "&&", "||", "$(", "`", ">", ">>", "<"]

BLOCKED_WINDOWS_PATHS = [
    "c:\\windows",
    "c:/windows",
    "c:\\windows\\system32",
    "c:/windows/system32",
    "c:\\windows\\syswow64",
    "c:/windows/syswow64",
    "c:\\windows\\winsxs",
    "c:/windows/winsxs",
    "c:\\windows\\temp",
    "c:/windows/temp",
    "c:\\windows\\logs",
    "c:/windows/logs",
    "c:\\program files",
    "c:/program files",
    "c:\\program files (x86)",
    "c:/program files (x86)",
    "c:\\programdata",
    "c:/programdata",
    "\\appdata",
    "/appdata/",
    "\\appdata\\local\\google",
    "/appdata/local/google",
    "\\appdata\\local\\microsoft\\edge",
    "/appdata/local/microsoft/edge",
    "\\appdata\\roaming\\mozilla",
    "/appdata/roaming/mozilla",
    "\\appdata\\roaming\\",
    "/appdata/roaming/",
    "\\appdata\\local\\",
    "/appdata/local/",
    "\\appdata\\locallow\\",
    "/appdata/locallow/",
    "\\.ssh",
    "/.ssh",
    "\\.aws",
    "/.aws",
    "\\.azure",
    "/.azure",
    "\\.docker",
    "/.docker",
    "\\.kube",
    "/.kube",
    "\\.gnupg",
    "/.gnupg",
    "\\.git-credentials",
    "/.git-credentials",
    "\\.npmrc",
    "/.npmrc",
    "\\.pypirc",
    "/.pypirc",
]

APP_COMMANDS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "explorer": "explorer.exe",
    "paint": "mspaint.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
}


class Point(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]


def safe_resolve(path):
    if not isinstance(path, str) or not path.strip():
        return None, {"error": "La ruta debe ser texto no vacio."}

    return Path(path).expanduser().resolve(), None


def open_application(args: OpenApplicationInput, ctx: ToolContext):
    normalized = args.app_name.strip().lower()
    command = APP_COMMANDS.get(normalized)

    if command is None:
        return {"error": f"Aplicacion no permitida: {args.app_name}", "allowed_apps": sorted(APP_COMMANDS)}

    subprocess.Popen([command])
    return {"opened": normalized, "command": command}


def open_notepad(args: EmptyInput, ctx: ToolContext):
    return open_application(OpenApplicationInput(app_name="notepad"), ctx)


def open_calculator(args: EmptyInput, ctx: ToolContext):
    return open_application(OpenApplicationInput(app_name="calculator"), ctx)


def get_system_info(args: EmptyInput, ctx: ToolContext):
    memory = psutil.virtual_memory()
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_cores": psutil.cpu_count(logical=False),
        "cpu_threads": psutil.cpu_count(logical=True),
        "ram_total_gb": round(memory.total / (1024 ** 3), 2),
        "ram_available_gb": round(memory.available / (1024 ** 3), 2),
        "ram_used_percent": memory.percent,
    }


def get_running_processes(args: LimitInput, ctx: ToolContext):
    processes = []

    for process in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        info = process.info
        processes.append({
            "pid": info["pid"],
            "name": info["name"],
            "cpu_percent": info["cpu_percent"],
            "memory_percent": round(info["memory_percent"], 2),
        })

    processes.sort(key=lambda item: item["memory_percent"], reverse=True)
    return processes[:args.limit]


def list_directory(args: DirectoryListInput, ctx: ToolContext):
    root, error = safe_resolve(args.path)

    if error:
        return error

    if not root.exists():
        return {"error": f"La ruta no existe: {root}"}

    if not root.is_dir():
        return {"error": f"La ruta no es una carpeta: {root}"}

    items = []

    for item in root.iterdir():
        try:
            stat = item.stat()
        except OSError:
            continue

        items.append({
            "name": item.name,
            "path": str(item),
            "type": "directory" if item.is_dir() else "file",
            "size_bytes": stat.st_size,
        })

        if len(items) >= args.limit:
            break

    return {"path": str(root), "count": len(items), "items": items}


def read_text_file(args: ReadTextFileInput, ctx: ToolContext):
    file_path, error = safe_resolve(args.path)

    if error:
        return error

    if not file_path.exists():
        return {"error": f"El archivo no existe: {file_path}"}

    if not file_path.is_file():
        return {"error": f"La ruta no es un archivo: {file_path}"}

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"error": "El archivo no parece ser texto UTF-8."}
    except PermissionError as error:
        return {"error": "Permiso denegado al leer archivo.", "details": str(error)}

    truncated = len(content) > args.max_chars
    return {
        "path": str(file_path),
        "content": content[:args.max_chars],
        "truncated": truncated,
        "chars": min(len(content), args.max_chars),
    }


def search_files(args: SearchFilesInput, ctx: ToolContext):
    if any(separator in args.pattern for separator in ["..", "/", "\\"]):
        return {"error": "El patron solo debe describir nombres de archivo, por ejemplo *.py."}

    root, error = safe_resolve(args.path)

    if error:
        return error

    if not root.exists():
        return {"error": f"La ruta no existe: {root}"}

    if not root.is_dir():
        return {"error": f"La ruta no es una carpeta: {root}"}

    matches = []

    try:
        for directory, dirnames, filenames in root.walk():
            dirnames[:] = [
                dirname
                for dirname in dirnames
                if dirname.lower() not in EXCLUDED_SEARCH_DIR_NAMES
            ]

            for filename in filenames:
                if not Path(filename).match(args.pattern):
                    continue

                file_path = directory / filename
                matches.append(str(file_path))

                if len(matches) >= args.limit:
                    return {"path": str(root), "pattern": args.pattern, "count": len(matches), "matches": matches}
    except PermissionError as error:
        return {"error": "Permiso denegado durante la busqueda.", "details": str(error), "matches": matches}

    return {"path": str(root), "pattern": args.pattern, "count": len(matches), "matches": matches}


def get_clipboard(args: EmptyInput, ctx: ToolContext):
    if pyperclip is None:
        return {"error": "pyperclip no esta instalado."}

    text = pyperclip.paste()
    truncated = len(text) > MAX_CLIPBOARD_CHARS
    return {"text": text[:MAX_CLIPBOARD_CHARS], "truncated": truncated, "chars": min(len(text), MAX_CLIPBOARD_CHARS)}


def set_clipboard(args: SetClipboardInput, ctx: ToolContext):
    if pyperclip is None:
        return {"error": "pyperclip no esta instalado."}

    pyperclip.copy(args.text)
    return {"copied": True, "chars": len(args.text)}


def get_mouse_position(args: EmptyInput, ctx: ToolContext):
    point = Point()
    windll.user32.GetCursorPos(byref(point))
    return {"x": point.x, "y": point.y}


def get_screen_size(args: EmptyInput, ctx: ToolContext):
    width = windll.user32.GetSystemMetrics(0)
    height = windll.user32.GetSystemMetrics(1)
    return {"width": width, "height": height}


def run_pyautogui_safely(action):
    if pyautogui is None:
        return False, "pyautogui no esta instalado."

    previous_failsafe = pyautogui.FAILSAFE
    pyautogui.FAILSAFE = False

    try:
        action()
        return True, None
    except Exception as error:
        return False, str(error)
    finally:
        pyautogui.FAILSAFE = previous_failsafe


def move_mouse(args: MoveMouseInput, ctx: ToolContext):
    screen = get_screen_size(EmptyInput(), ctx)
    x = max(0, min(args.x, min(MAX_MOUSE_COORDINATE, screen["width"] - 1)))
    y = max(0, min(args.y, min(MAX_MOUSE_COORDINATE, screen["height"] - 1)))
    methods = []

    ok, error = run_pyautogui_safely(lambda: pyautogui.moveTo(x, y, duration=args.duration))
    methods.append({"method": "pyautogui.moveTo", "ok": ok, "error": error})

    position = get_mouse_position(EmptyInput(), ctx)

    if position["x"] != x or position["y"] != y:
        result = bool(windll.user32.SetCursorPos(x, y))
        methods.append({
            "method": "user32.SetCursorPos",
            "ok": result,
            "error": None if result else "Windows no permitio mover el cursor desde este proceso.",
        })

    position = get_mouse_position(EmptyInput(), ctx)
    return {
        "moved": position["x"] == x and position["y"] == y,
        "x": position["x"],
        "y": position["y"],
        "requested_x": x,
        "requested_y": y,
        "duration": args.duration,
        "screen": screen,
        "methods": methods,
    }


def click_mouse(args: ClickMouseInput, ctx: ToolContext):
    if pyautogui is None:
        return {"error": "pyautogui no esta instalado."}

    if args.button not in {"left", "right", "middle"}:
        return {"error": "button debe ser left, right o middle."}

    ok, error = run_pyautogui_safely(lambda: pyautogui.click(button=args.button, clicks=args.clicks))

    if not ok:
        return {"error": "No se pudo hacer click.", "details": error}

    return {"clicked": True, "button": args.button, "clicks": args.clicks}


def press_key(args: PressKeyInput, ctx: ToolContext):
    if pyautogui is None:
        return {"error": "pyautogui no esta instalado."}

    normalized_key = args.key.strip().lower()
    ok, error = run_pyautogui_safely(lambda: pyautogui.press(normalized_key))

    if not ok:
        return {"error": "No se pudo pulsar la tecla.", "details": error}

    return {"pressed": normalized_key}


def hotkey(args: HotkeyInput, ctx: ToolContext):
    if pyautogui is None:
        return {"error": "pyautogui no esta instalado."}

    normalized_keys = [key.strip().lower() for key in args.keys]
    ok, error = run_pyautogui_safely(lambda: pyautogui.hotkey(*normalized_keys))

    if not ok:
        return {"error": "No se pudo ejecutar el hotkey.", "details": error}

    return {"hotkey": normalized_keys}


def type_text(args: TypeTextInput, ctx: ToolContext):
    if pyautogui is None:
        return {"error": "pyautogui no esta instalado."}

    ok, error = run_pyautogui_safely(lambda: pyautogui.write(args.text, interval=args.interval))

    if not ok:
        return {"error": "No se pudo escribir texto.", "details": error}

    return {"typed": True, "chars": len(args.text)}


def open_url(args: OpenUrlInput, ctx: ToolContext):
    normalized = args.url.strip()

    if not normalized.startswith(("http://", "https://")):
        return {"error": "Solo se permiten URLs http:// o https://."}

    webbrowser.open(normalized)
    return {"opened": normalized}


def get_powershell_command_names(command):
    names = []

    for segment in command.split("|"):
        cleaned_segment = segment.strip()

        if not cleaned_segment:
            continue

        names.append(cleaned_segment.split()[0].lower())

    return names


def validate_powershell_command(command):
    if not isinstance(command, str) or not command.strip():
        return "El comando debe ser texto no vacio."

    normalized_command = command.strip().lower()

    for blocked_token in BLOCKED_POWERSHELL_TOKENS:
        if blocked_token in normalized_command:
            return f"Token no permitido en PowerShell: {blocked_token}"

    for blocked_path in BLOCKED_WINDOWS_PATHS:
        if blocked_path in normalized_command:
            return f"Ruta Windows bloqueada en PowerShell: {blocked_path}"

    command_names = get_powershell_command_names(normalized_command)

    if not command_names:
        return "No se encontro ningun comando PowerShell."

    for command_name in command_names:
        if command_name not in ALLOWED_POWERSHELL_COMMANDS:
            return f"Comando PowerShell no permitido: {command_name}"

    return None


def run_powershell(args: PowerShellInput, ctx: ToolContext):
    validation_error = validate_powershell_command(args.command)

    if validation_error:
        return {"blocked": True, "reason": validation_error, "allowed_commands": sorted(ALLOWED_POWERSHELL_COMMANDS)}

    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", args.command],
            capture_output=True,
            text=True,
            timeout=args.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"blocked": True, "reason": f"El comando supero el timeout de {args.timeout} segundos."}

    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def tool(name, description, schema, handler, *, category, aliases=(), tags=(), capabilities=(), risk_level=RiskLevel.USER_CONFIRM, requires_confirmation=True, timeout_seconds=15):
    return ToolDefinition(
        metadata=ToolMetadata(
            name=name,
            description=description,
            category=category,
            aliases=aliases,
            tags=tags,
            capabilities=capabilities,
            risk_level=risk_level,
            requires_confirmation=requires_confirmation,
            timeout_seconds=timeout_seconds,
        ),
        input_schema=schema,
        handler=handler,
    )


def build_local_tool_definitions():
    return [
        tool("open_application", "Abre una aplicacion Windows permitida por allowlist.", OpenApplicationInput, open_application, aliases=("app",), category="windows", tags=("automation",)),
        tool("open_notepad", "Abre el Bloc de notas de Windows.", EmptyInput, open_notepad, aliases=("notepad",), category="windows", tags=("automation",)),
        tool("open_calculator", "Abre la calculadora de Windows.", EmptyInput, open_calculator, aliases=("calc",), category="windows", tags=("automation",)),
        tool("get_system_info", "Obtiene informacion basica del sistema, CPU y memoria RAM.", EmptyInput, get_system_info, aliases=("sistema",), category="system", tags=("read_only",), capabilities=("system.inspect",), risk_level=RiskLevel.SAFE, requires_confirmation=False),
        tool("get_running_processes", "Lista procesos activos ordenados por uso de memoria.", LimitInput, get_running_processes, category="system", tags=("read_only",), capabilities=("process.inspect",), risk_level=RiskLevel.READ_ONLY, requires_confirmation=False),
        tool("list_directory", "Lista archivos y carpetas dentro de una ruta.", DirectoryListInput, list_directory, category="filesystem", tags=("read_only",), capabilities=("filesystem.read",), risk_level=RiskLevel.READ_ONLY),
        tool("read_text_file", "Lee un archivo de texto UTF-8 con limite de caracteres.", ReadTextFileInput, read_text_file, category="filesystem", tags=("read_only",), capabilities=("filesystem.read",), risk_level=RiskLevel.READ_ONLY),
        tool("search_files", "Busca archivos dentro de una carpeta usando un patron glob.", SearchFilesInput, search_files, category="filesystem", tags=("read_only",), capabilities=("filesystem.search",), risk_level=RiskLevel.READ_ONLY),
        tool("get_clipboard", "Devuelve texto del portapapeles.", EmptyInput, get_clipboard, category="clipboard", tags=("read_only",), risk_level=RiskLevel.READ_ONLY),
        tool("set_clipboard", "Copia texto al portapapeles.", SetClipboardInput, set_clipboard, category="clipboard", capabilities=("clipboard.write",)),
        tool("get_mouse_position", "Devuelve la posicion actual del raton.", EmptyInput, get_mouse_position, category="automation", tags=("read_only",), risk_level=RiskLevel.SAFE, requires_confirmation=False),
        tool("get_screen_size", "Devuelve el tamano de la pantalla principal.", EmptyInput, get_screen_size, category="automation", tags=("read_only",), risk_level=RiskLevel.SAFE, requires_confirmation=False),
        tool("move_mouse", "Mueve el raton a una coordenada de pantalla.", MoveMouseInput, move_mouse, category="automation", capabilities=("mouse.move",)),
        tool("click_mouse", "Hace click con el raton.", ClickMouseInput, click_mouse, category="automation", capabilities=("mouse.click",)),
        tool("press_key", "Pulsa una tecla.", PressKeyInput, press_key, category="automation", capabilities=("keyboard.press",)),
        tool("hotkey", "Pulsa una combinacion de teclas.", HotkeyInput, hotkey, category="automation", capabilities=("keyboard.hotkey",)),
        tool("type_text", "Escribe texto usando el teclado.", TypeTextInput, type_text, category="automation", capabilities=("keyboard.type",)),
        tool("open_url", "Abre una URL http/https en el navegador predeterminado.", OpenUrlInput, open_url, aliases=("browser_open",), category="browser", capabilities=("browser.open",)),
        tool("run_powershell", "Ejecuta comandos PowerShell de solo inspeccion permitidos por allowlist.", PowerShellInput, run_powershell, category="powershell", tags=("read_only",), capabilities=("powershell.inspect",), risk_level=RiskLevel.READ_ONLY),
    ]
