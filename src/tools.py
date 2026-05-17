"""Sistema de tools locales para el agente.

Este modulo define un registro de tools con metadatos, schemas OpenAI-compatible
y funciones ejecutoras. Es la frontera controlada entre el modelo y Windows.
"""

import platform
import subprocess
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from ctypes import Structure, byref, c_long, windll

import psutil

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import pyperclip
except ImportError:
    pyperclip = None


MAX_PROCESS_LIMIT = 50
MAX_SEARCH_LIMIT = 100
MAX_DIRECTORY_LIMIT = 100
MAX_FILE_READ_CHARS = 12000
MAX_CLIPBOARD_CHARS = 8000
MAX_POWERSHELL_TIMEOUT = 15
MAX_POWERSHELL_COMMAND_LENGTH = 300
MAX_MOUSE_COORDINATE = 10000
MAX_KEYBOARD_TEXT_LENGTH = 500

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

BLOCKED_POWERSHELL_TOKENS = [
    ";",
    "&&",
    "||",
    "$(",
    "`",
    ">",
    ">>",
    "<",
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
    _fields_ = [
        ("x", c_long),
        ("y", c_long),
    ]


@dataclass(frozen=True)
class ToolDefinition:
    """Definicion registrable de una tool."""

    name: str
    description: str
    parameters: dict
    handler: callable
    aliases: tuple = ()
    category: str = "general"
    requires_confirmation: bool = True

    def schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Registro centralizado de tools."""

    def __init__(self):
        self._tools = {}
        self._aliases = {}

    def register(self, definition):
        self._tools[definition.name] = definition

        for alias in definition.aliases:
            self._aliases[alias] = definition.name

    def get(self, name):
        canonical_name = self._aliases.get(name, name)
        return self._tools.get(canonical_name)

    def schemas(self):
        return [definition.schema() for definition in self._tools.values()]

    def names(self):
        return sorted([*self._tools.keys(), *self._aliases.keys()])

    def run(self, name, arguments=None):
        definition = self.get(name)

        if definition is None:
            return f"Tool no encontrada. Disponibles: {', '.join(self.names())}"

        if arguments is None:
            arguments = {}

        try:
            return definition.handler(**arguments)
        except TypeError as error:
            return {
                "error": "Argumentos invalidos para la tool.",
                "details": str(error),
            }
        except Exception as error:
            return {
                "error": "La tool fallo durante la ejecucion.",
                "details": str(error),
            }


def object_schema(properties=None, required=None):
    return {
        "type": "object",
        "properties": properties or {},
        "required": required or [],
        "additionalProperties": False,
    }


def clamp_int(value, default, minimum, maximum):
    """Convierte un valor a entero y lo limita dentro de un rango seguro."""
    if value is None:
        return default

    try:
        number = int(value)
    except (TypeError, ValueError):
        return default

    return max(minimum, min(number, maximum))


def clamp_float(value, default, minimum, maximum):
    if value is None:
        return default

    try:
        number = float(value)
    except (TypeError, ValueError):
        return default

    return max(minimum, min(number, maximum))


def safe_resolve(path):
    if not isinstance(path, str) or not path.strip():
        return None, {"error": "La ruta debe ser texto no vacio."}

    return Path(path).expanduser().resolve(), None


def open_application(app_name):
    """Abre una aplicacion Windows permitida."""
    if not isinstance(app_name, str) or not app_name.strip():
        return {"error": "app_name debe ser texto no vacio."}

    normalized = app_name.strip().lower()
    command = APP_COMMANDS.get(normalized)

    if command is None:
        return {
            "error": f"Aplicacion no permitida: {app_name}",
            "allowed_apps": sorted(APP_COMMANDS),
        }

    subprocess.Popen([command])
    return {"opened": normalized, "command": command}


def open_notepad():
    """Abre el Bloc de notas de Windows."""
    return open_application("notepad")


def open_calculator():
    """Abre la calculadora de Windows."""
    return open_application("calculator")


def get_system_info():
    """Devuelve informacion basica del sistema, CPU y memoria RAM."""
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


def get_running_processes(limit=15):
    """Lista procesos activos ordenados por uso de memoria."""
    limit = clamp_int(limit, default=15, minimum=1, maximum=MAX_PROCESS_LIMIT)
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
    return processes[:limit]


def list_directory(path=".", limit=50):
    """Lista archivos y carpetas de una ruta."""
    limit = clamp_int(limit, default=50, minimum=1, maximum=MAX_DIRECTORY_LIMIT)
    root, error = safe_resolve(path)

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

        if len(items) >= limit:
            break

    return {
        "path": str(root),
        "count": len(items),
        "items": items,
    }


def read_text_file(path, max_chars=MAX_FILE_READ_CHARS):
    """Lee un archivo de texto con limite de caracteres."""
    max_chars = clamp_int(max_chars, default=MAX_FILE_READ_CHARS, minimum=1, maximum=MAX_FILE_READ_CHARS)
    file_path, error = safe_resolve(path)

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

    truncated = len(content) > max_chars
    return {
        "path": str(file_path),
        "content": content[:max_chars],
        "truncated": truncated,
        "chars": min(len(content), max_chars),
    }


def search_files(path, pattern, limit=20):
    """Busca archivos en una carpeta usando un patron glob simple."""
    limit = clamp_int(limit, default=20, minimum=1, maximum=MAX_SEARCH_LIMIT)

    if not isinstance(pattern, str) or not pattern.strip():
        return {"error": "El patron debe ser texto no vacio."}

    if any(separator in pattern for separator in ["..", "/", "\\"]):
        return {"error": "El patron solo debe describir nombres de archivo, por ejemplo *.py."}

    root, error = safe_resolve(path)

    if error:
        return error

    if not root.exists():
        return {"error": f"La ruta no existe: {root}"}

    if not root.is_dir():
        return {"error": f"La ruta no es una carpeta: {root}"}

    matches = []

    try:
        for file_path in root.rglob(pattern):
            matches.append(str(file_path))

            if len(matches) >= limit:
                break
    except PermissionError as error:
        return {
            "error": "Permiso denegado durante la busqueda.",
            "details": str(error),
            "matches": matches,
        }

    return {
        "path": str(root),
        "pattern": pattern,
        "count": len(matches),
        "matches": matches,
    }


def get_clipboard():
    """Devuelve texto del portapapeles."""
    if pyperclip is None:
        return {"error": "pyperclip no esta instalado."}

    text = pyperclip.paste()
    truncated = len(text) > MAX_CLIPBOARD_CHARS
    return {
        "text": text[:MAX_CLIPBOARD_CHARS],
        "truncated": truncated,
        "chars": min(len(text), MAX_CLIPBOARD_CHARS),
    }


def set_clipboard(text):
    """Escribe texto en el portapapeles."""
    if pyperclip is None:
        return {"error": "pyperclip no esta instalado."}

    if not isinstance(text, str):
        return {"error": "text debe ser una cadena."}

    if len(text) > MAX_CLIPBOARD_CHARS:
        return {"error": f"text supera {MAX_CLIPBOARD_CHARS} caracteres."}

    pyperclip.copy(text)
    return {"copied": True, "chars": len(text)}


def get_mouse_position():
    """Devuelve la posicion actual del raton."""
    point = Point()
    windll.user32.GetCursorPos(byref(point))
    return {"x": point.x, "y": point.y}


def get_screen_size():
    """Devuelve el tamano de la pantalla principal."""
    width = windll.user32.GetSystemMetrics(0)
    height = windll.user32.GetSystemMetrics(1)
    return {"width": width, "height": height}


def run_pyautogui_safely(action):
    """Ejecuta una accion pyautogui sin disparar fail-safe por estar en una esquina."""
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


def move_mouse(x, y, duration=0.2):
    """Mueve el raton a una coordenada de pantalla."""
    screen = get_screen_size()
    x = clamp_int(x, default=0, minimum=0, maximum=min(MAX_MOUSE_COORDINATE, screen["width"] - 1))
    y = clamp_int(y, default=0, minimum=0, maximum=min(MAX_MOUSE_COORDINATE, screen["height"] - 1))
    duration = clamp_float(duration, default=0, minimum=0, maximum=3)
    methods = []

    ok, error = run_pyautogui_safely(lambda: pyautogui.moveTo(x, y, duration=duration))
    methods.append({
        "method": "pyautogui.moveTo",
        "ok": ok,
        "error": error,
    })

    position = get_mouse_position()

    if position["x"] != x or position["y"] != y:
        result = bool(windll.user32.SetCursorPos(x, y))
        methods.append({
            "method": "user32.SetCursorPos",
            "ok": result,
            "error": None if result else "Windows no permitio mover el cursor desde este proceso.",
        })

    position = get_mouse_position()
    return {
        "moved": position["x"] == x and position["y"] == y,
        "x": position["x"],
        "y": position["y"],
        "requested_x": x,
        "requested_y": y,
        "duration": duration,
        "screen": screen,
        "methods": methods,
    }


def click_mouse(button="left", clicks=1):
    """Hace click con el raton."""
    if pyautogui is None:
        return {"error": "pyautogui no esta instalado."}

    if button not in {"left", "right", "middle"}:
        return {"error": "button debe ser left, right o middle."}

    clicks = clamp_int(clicks, default=1, minimum=1, maximum=3)
    ok, error = run_pyautogui_safely(lambda: pyautogui.click(button=button, clicks=clicks))

    if not ok:
        return {"error": "No se pudo hacer click.", "details": error}

    return {"clicked": True, "button": button, "clicks": clicks}


def press_key(key):
    """Pulsa una tecla."""
    if pyautogui is None:
        return {"error": "pyautogui no esta instalado."}

    if not isinstance(key, str) or not key.strip():
        return {"error": "key debe ser texto no vacio."}

    normalized_key = key.strip().lower()
    ok, error = run_pyautogui_safely(lambda: pyautogui.press(normalized_key))

    if not ok:
        return {"error": "No se pudo pulsar la tecla.", "details": error}

    return {"pressed": normalized_key}


def hotkey(keys):
    """Pulsa una combinacion de teclas."""
    if pyautogui is None:
        return {"error": "pyautogui no esta instalado."}

    if not isinstance(keys, list) or not keys:
        return {"error": "keys debe ser una lista no vacia."}

    normalized_keys = []

    for key in keys[:5]:
        if not isinstance(key, str) or not key.strip():
            return {"error": "Todas las teclas deben ser texto no vacio."}

        normalized_keys.append(key.strip().lower())

    ok, error = run_pyautogui_safely(lambda: pyautogui.hotkey(*normalized_keys))

    if not ok:
        return {"error": "No se pudo ejecutar el hotkey.", "details": error}

    return {"hotkey": normalized_keys}


def type_text(text, interval=0.02):
    """Escribe texto con el teclado."""
    if pyautogui is None:
        return {"error": "pyautogui no esta instalado."}

    if not isinstance(text, str):
        return {"error": "text debe ser una cadena."}

    if len(text) > MAX_KEYBOARD_TEXT_LENGTH:
        return {"error": f"text supera {MAX_KEYBOARD_TEXT_LENGTH} caracteres."}

    interval = clamp_float(interval, default=0.02, minimum=0, maximum=0.5)
    ok, error = run_pyautogui_safely(lambda: pyautogui.write(text, interval=interval))

    if not ok:
        return {"error": "No se pudo escribir texto.", "details": error}

    return {"typed": True, "chars": len(text)}


def open_url(url):
    """Abre una URL en el navegador predeterminado."""
    if not isinstance(url, str) or not url.strip():
        return {"error": "url debe ser texto no vacio."}

    normalized = url.strip()

    if not normalized.startswith(("http://", "https://")):
        return {"error": "Solo se permiten URLs http:// o https://."}

    webbrowser.open(normalized)
    return {"opened": normalized}


def get_powershell_command_names(command):
    """Extrae los nombres de comandos usados en una cadena PowerShell."""
    names = []

    for segment in command.split("|"):
        cleaned_segment = segment.strip()

        if not cleaned_segment:
            continue

        command_name = cleaned_segment.split()[0].lower()
        names.append(command_name)

    return names


def validate_powershell_command(command):
    """Valida que un comando PowerShell sea de inspeccion y este permitido."""
    if not isinstance(command, str) or not command.strip():
        return "El comando debe ser texto no vacio."

    if len(command) > MAX_POWERSHELL_COMMAND_LENGTH:
        return f"El comando supera el maximo de {MAX_POWERSHELL_COMMAND_LENGTH} caracteres."

    normalized_command = command.strip().lower()

    for blocked_token in BLOCKED_POWERSHELL_TOKENS:
        if blocked_token in normalized_command:
            return f"Token no permitido en PowerShell: {blocked_token}"

    command_names = get_powershell_command_names(normalized_command)

    if not command_names:
        return "No se encontro ningun comando PowerShell."

    for command_name in command_names:
        if command_name not in ALLOWED_POWERSHELL_COMMANDS:
            return f"Comando PowerShell no permitido: {command_name}"

    return None


def run_powershell(command, timeout=10):
    """Ejecuta un comando PowerShell permitido y devuelve su salida."""
    timeout = clamp_int(
        timeout,
        default=10,
        minimum=1,
        maximum=MAX_POWERSHELL_TIMEOUT,
    )

    validation_error = validate_powershell_command(command)

    if validation_error:
        return {
            "blocked": True,
            "reason": validation_error,
            "allowed_commands": sorted(ALLOWED_POWERSHELL_COMMANDS),
        }

    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "blocked": True,
            "reason": f"El comando supero el timeout de {timeout} segundos.",
        }

    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def build_tool_registry():
    registry = ToolRegistry()

    registry.register(ToolDefinition(
        name="open_application",
        description="Abre una aplicacion Windows permitida por allowlist.",
        parameters=object_schema({
            "app_name": {
                "type": "string",
                "description": "Aplicacion permitida: notepad, calculator, explorer, paint, cmd o powershell.",
            },
        }, ["app_name"]),
        handler=open_application,
        aliases=("app",),
        category="windows",
    ))
    registry.register(ToolDefinition(
        name="open_notepad",
        description="Abre el Bloc de notas de Windows.",
        parameters=object_schema(),
        handler=open_notepad,
        aliases=("notepad",),
        category="windows",
    ))
    registry.register(ToolDefinition(
        name="open_calculator",
        description="Abre la calculadora de Windows.",
        parameters=object_schema(),
        handler=open_calculator,
        aliases=("calc",),
        category="windows",
    ))
    registry.register(ToolDefinition(
        name="get_system_info",
        description="Obtiene informacion basica del sistema, CPU y memoria RAM.",
        parameters=object_schema(),
        handler=get_system_info,
        aliases=("sistema",),
        category="system",
        requires_confirmation=False,
    ))
    registry.register(ToolDefinition(
        name="get_running_processes",
        description="Lista procesos activos ordenados por uso de memoria.",
        parameters=object_schema({
            "limit": {
                "type": "integer",
                "description": "Numero maximo de procesos a devolver. Maximo 50.",
                "default": 15,
            },
        }),
        handler=get_running_processes,
        category="system",
        requires_confirmation=False,
    ))
    registry.register(ToolDefinition(
        name="list_directory",
        description="Lista archivos y carpetas dentro de una ruta.",
        parameters=object_schema({
            "path": {"type": "string", "description": "Carpeta a listar.", "default": "."},
            "limit": {"type": "integer", "description": "Maximo 100 elementos.", "default": 50},
        }),
        handler=list_directory,
        category="filesystem",
    ))
    registry.register(ToolDefinition(
        name="read_text_file",
        description="Lee un archivo de texto UTF-8 con limite de caracteres.",
        parameters=object_schema({
            "path": {"type": "string", "description": "Archivo a leer."},
            "max_chars": {
                "type": "integer",
                "description": f"Caracteres maximos. Maximo {MAX_FILE_READ_CHARS}.",
                "default": MAX_FILE_READ_CHARS,
            },
        }, ["path"]),
        handler=read_text_file,
        category="filesystem",
    ))
    registry.register(ToolDefinition(
        name="search_files",
        description="Busca archivos dentro de una carpeta usando un patron glob.",
        parameters=object_schema({
            "path": {"type": "string", "description": "Carpeta donde buscar."},
            "pattern": {"type": "string", "description": "Patron glob, por ejemplo *.pdf o *.py."},
            "limit": {"type": "integer", "description": "Numero maximo de resultados. Maximo 100.", "default": 20},
        }, ["path", "pattern"]),
        handler=search_files,
        category="filesystem",
    ))
    registry.register(ToolDefinition(
        name="get_clipboard",
        description="Devuelve texto del portapapeles.",
        parameters=object_schema(),
        handler=get_clipboard,
        category="clipboard",
    ))
    registry.register(ToolDefinition(
        name="set_clipboard",
        description="Copia texto al portapapeles.",
        parameters=object_schema({
            "text": {"type": "string", "description": "Texto a copiar. Maximo 8000 caracteres."},
        }, ["text"]),
        handler=set_clipboard,
        category="clipboard",
    ))
    registry.register(ToolDefinition(
        name="get_mouse_position",
        description="Devuelve la posicion actual del raton.",
        parameters=object_schema(),
        handler=get_mouse_position,
        category="automation",
        requires_confirmation=False,
    ))
    registry.register(ToolDefinition(
        name="get_screen_size",
        description="Devuelve el tamano de la pantalla principal.",
        parameters=object_schema(),
        handler=get_screen_size,
        category="automation",
        requires_confirmation=False,
    ))
    registry.register(ToolDefinition(
        name="move_mouse",
        description="Mueve el raton a una coordenada de pantalla.",
        parameters=object_schema({
            "x": {"type": "integer", "description": "Coordenada X."},
            "y": {"type": "integer", "description": "Coordenada Y."},
            "duration": {"type": "number", "description": "Duracion del movimiento en segundos.", "default": 0.2},
        }, ["x", "y"]),
        handler=move_mouse,
        category="automation",
    ))
    registry.register(ToolDefinition(
        name="click_mouse",
        description="Hace click con el raton.",
        parameters=object_schema({
            "button": {"type": "string", "description": "left, right o middle.", "default": "left"},
            "clicks": {"type": "integer", "description": "Numero de clicks. Maximo 3.", "default": 1},
        }),
        handler=click_mouse,
        category="automation",
    ))
    registry.register(ToolDefinition(
        name="press_key",
        description="Pulsa una tecla.",
        parameters=object_schema({
            "key": {"type": "string", "description": "Nombre de tecla pyautogui, por ejemplo enter, esc, tab."},
        }, ["key"]),
        handler=press_key,
        category="automation",
    ))
    registry.register(ToolDefinition(
        name="hotkey",
        description="Pulsa una combinacion de teclas.",
        parameters=object_schema({
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Lista de teclas, por ejemplo ['ctrl', 'c']. Maximo 5.",
            },
        }, ["keys"]),
        handler=hotkey,
        category="automation",
    ))
    registry.register(ToolDefinition(
        name="type_text",
        description="Escribe texto usando el teclado.",
        parameters=object_schema({
            "text": {"type": "string", "description": "Texto a escribir. Maximo 500 caracteres."},
            "interval": {"type": "number", "description": "Pausa entre caracteres.", "default": 0.02},
        }, ["text"]),
        handler=type_text,
        category="automation",
    ))
    registry.register(ToolDefinition(
        name="open_url",
        description="Abre una URL http/https en el navegador predeterminado.",
        parameters=object_schema({
            "url": {"type": "string", "description": "URL http:// o https://."},
        }, ["url"]),
        handler=open_url,
        aliases=("browser_open",),
        category="browser",
    ))
    registry.register(ToolDefinition(
        name="run_powershell",
        description="Ejecuta comandos PowerShell de solo inspeccion permitidos por allowlist y devuelve stdout, stderr y codigo de salida.",
        parameters=object_schema({
            "command": {
                "type": "string",
                "description": "Comando PowerShell permitido, por ejemplo Get-Date, Get-Process, Get-Service o Test-Path.",
            },
            "timeout": {
                "type": "integer",
                "description": "Tiempo maximo de ejecucion en segundos. Maximo 15.",
                "default": 10,
            },
        }, ["command"]),
        handler=run_powershell,
        category="powershell",
    ))

    return registry


TOOL_REGISTRY = build_tool_registry()
TOOL_SCHEMAS = TOOL_REGISTRY.schemas()
TOOLS = {
    name: TOOL_REGISTRY.get(name).handler
    for name in TOOL_REGISTRY.names()
    if TOOL_REGISTRY.get(name) is not None
}


def run_tool(name, arguments=None):
    """Ejecuta una tool registrada por nombre con argumentos opcionales."""
    return TOOL_REGISTRY.run(name, arguments)
