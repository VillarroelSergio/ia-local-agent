import platform
import subprocess
from pathlib import Path

import psutil


MAX_PROCESS_LIMIT = 50
MAX_SEARCH_LIMIT = 100
MAX_POWERSHELL_TIMEOUT = 15
MAX_POWERSHELL_COMMAND_LENGTH = 300

ALLOWED_POWERSHELL_COMMANDS = {
    "get-date",
    "get-process",
    "get-service",
    "get-computerinfo",
    "get-childitem",
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


def clamp_int(value, default, minimum, maximum):
    if value is None:
        return default

    try:
        number = int(value)
    except (TypeError, ValueError):
        return default

    return max(minimum, min(number, maximum))


def open_notepad():
    subprocess.Popen(["notepad.exe"])
    return "Notepad abierto."


def open_calculator():
    subprocess.Popen(["calc.exe"])
    return "Calculadora abierta."


def get_system_info():
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


def search_files(path, pattern, limit=20):
    limit = clamp_int(limit, default=20, minimum=1, maximum=MAX_SEARCH_LIMIT)

    if not isinstance(path, str) or not path.strip():
        return {"error": "La ruta debe ser texto no vacio."}

    if not isinstance(pattern, str) or not pattern.strip():
        return {"error": "El patron debe ser texto no vacio."}

    if any(separator in pattern for separator in ["..", "/", "\\"]):
        return {"error": "El patron solo debe describir nombres de archivo, por ejemplo *.py."}

    root = Path(path).expanduser().resolve()

    if not root.exists():
        return {"error": f"La ruta no existe: {root}"}

    if not root.is_dir():
        return {"error": f"La ruta no es una carpeta: {root}"}

    matches = []

    try:
        file_paths = root.rglob(pattern)

        for file_path in file_paths:
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


def get_powershell_command_names(command):
    names = []

    for segment in command.split("|"):
        cleaned_segment = segment.strip()

        if not cleaned_segment:
            continue

        command_name = cleaned_segment.split()[0].lower()
        names.append(command_name)

    return names


def validate_powershell_command(command):
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


TOOLS = {
    "notepad": open_notepad,
    "calc": open_calculator,
    "sistema": get_system_info,
    "open_notepad": open_notepad,
    "open_calculator": open_calculator,
    "get_system_info": get_system_info,
    "get_running_processes": get_running_processes,
    "search_files": search_files,
    "run_powershell": run_powershell,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "open_notepad",
            "description": "Abre el Bloc de notas de Windows.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_calculator",
            "description": "Abre la calculadora de Windows.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Obtiene informacion basica del sistema, CPU y memoria RAM.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_running_processes",
            "description": "Lista procesos activos ordenados por uso de memoria.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Numero maximo de procesos a devolver. Maximo 50.",
                        "default": 15,
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Busca archivos dentro de una carpeta usando un patron glob.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Carpeta donde buscar.",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Patron glob, por ejemplo *.pdf o *.py.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Numero maximo de resultados. Maximo 100.",
                        "default": 20,
                    },
                },
                "required": ["path", "pattern"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_powershell",
            "description": "Ejecuta comandos PowerShell de solo inspeccion permitidos por allowlist y devuelve stdout, stderr y codigo de salida.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Comando PowerShell permitido, por ejemplo Get-Date, Get-Process, Get-Service o Test-Path.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Tiempo maximo de ejecucion en segundos. Maximo 15.",
                        "default": 10,
                    },
                },
                "required": ["command"],
                "additionalProperties": False,
            },
        },
    },
]


def run_tool(name, arguments=None):
    tool = TOOLS.get(name)

    if tool is None:
        available_tools = ", ".join(TOOLS)
        return f"Tool no encontrada. Disponibles: {available_tools}"

    if arguments is None:
        arguments = {}

    try:
        return tool(**arguments)
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
