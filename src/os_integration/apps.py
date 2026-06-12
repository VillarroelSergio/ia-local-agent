"""Installed application discovery and launching for Windows."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

try:
    import winreg
except ImportError:
    winreg = None


@dataclass(frozen=True)
class InstalledApplication:
    name: str
    launch_path: str
    source: str
    kind: str = "executable"


@dataclass(frozen=True)
class LaunchResult:
    opened: bool
    query: str
    app: InstalledApplication | None = None
    error: str | None = None
    matches: tuple[InstalledApplication, ...] = ()


class ApplicationManager:
    """Resolves user-facing app names to installed apps without shell injection."""

    denied_name_fragments = (
        "credential",
        "password",
        "contraseña",
        "regedit",
        "registry editor",
        "uac",
        "local security policy",
        "services",
        "task scheduler",
        "windows powershell ise",
    )

    builtin_commands = {
        "notepad": "notepad.exe",
        "bloc de notas": "notepad.exe",
        "calculator": "calc.exe",
        "calculadora": "calc.exe",
        "calc": "calc.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "paint": "mspaint.exe",
        "cmd": "cmd.exe",
        "terminal": "wt.exe",
        "powershell": "powershell.exe",
        "spotify": ("spotify:", "url"),
    }

    def __init__(self):
        self._cache: tuple[InstalledApplication, ...] | None = None

    def list_installed_apps(self, *, refresh: bool = False, limit: int = 500) -> tuple[InstalledApplication, ...]:
        if self._cache is not None and not refresh:
            return self._cache[:limit]

        apps: dict[str, InstalledApplication] = {}
        for app in [*self._from_builtins(), *self._from_app_paths(), *self._from_start_menu()]:
            key = self._normalize(app.name)
            if key and key not in apps:
                apps[key] = app

        self._cache = tuple(sorted(apps.values(), key=lambda item: item.name.lower()))
        return self._cache[:limit]

    def find(self, query: str, *, limit: int = 10) -> tuple[InstalledApplication, ...]:
        normalized = self._normalize(query)
        if not normalized:
            return ()

        apps = self.list_installed_apps()
        exact_name = [
            app for app in apps
            if normalized == self._normalize(app.name)
        ]
        if exact_name:
            return tuple(exact_name[:limit])

        exact_executable = [
            app for app in apps
            if normalized == self._normalize(Path(app.launch_path).stem)
        ]
        if exact_executable:
            return tuple(exact_executable[:limit])

        contains = [
            app for app in apps
            if normalized in self._normalize(app.name)
            or normalized in self._normalize(Path(app.launch_path).name)
        ]
        if contains:
            return tuple(contains[:limit])

        executable = shutil.which(query)
        if executable:
            return (InstalledApplication(query, executable, "PATH", "executable"),)

        return ()

    def launch(self, query: str) -> LaunchResult:
        if self._is_denied(query):
            return LaunchResult(False, query, error="Aplicacion bloqueada por politica OS.")

        matches = self.find(query)
        if not matches:
            return LaunchResult(False, query, error="No se encontro una aplicacion instalada con ese nombre.")
        if len(matches) > 1:
            return LaunchResult(False, query, error="Coincidencia ambigua; especifica mejor el nombre.", matches=matches[:5])

        app = matches[0]
        if self._is_denied(app.name) or self._is_denied(app.launch_path):
            return LaunchResult(False, query, app=app, error="Aplicacion bloqueada por politica OS.")

        try:
            if app.kind in {"shortcut", "url", "appref"}:
                os.startfile(app.launch_path)
            else:
                subprocess.Popen([app.launch_path], close_fds=True)
        except OSError as error:
            return LaunchResult(False, query, app=app, error=str(error))

        return LaunchResult(True, query, app=app)

    def _from_builtins(self) -> list[InstalledApplication]:
        apps = []
        for name, command in self.builtin_commands.items():
            if isinstance(command, tuple):
                launch_path, kind = command
            else:
                launch_path, kind = command, "executable"
            apps.append(InstalledApplication(name, launch_path, "builtin", kind))
        return apps

    def _from_app_paths(self) -> list[InstalledApplication]:
        if winreg is None:
            return []
        apps: list[InstalledApplication] = []
        roots = (
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
        )
        for root, path in roots:
            try:
                with winreg.OpenKey(root, path) as key:
                    count = winreg.QueryInfoKey(key)[0]
                    for index in range(count):
                        subkey_name = winreg.EnumKey(key, index)
                        try:
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                value, _ = winreg.QueryValueEx(subkey, None)
                                if isinstance(value, str) and value.strip():
                                    launch_path = os.path.expandvars(value.strip('"'))
                                    apps.append(InstalledApplication(Path(subkey_name).stem, launch_path, "registry_app_paths"))
                        except OSError:
                            continue
            except OSError:
                continue
        return apps

    def _from_start_menu(self) -> list[InstalledApplication]:
        roots = [
            Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        ]
        apps: list[InstalledApplication] = []
        for root in roots:
            if not root.exists():
                continue
            for suffix, kind in (("*.lnk", "shortcut"), ("*.appref-ms", "appref"), ("*.url", "url")):
                for item in root.rglob(suffix):
                    name = item.stem
                    if name and not self._is_denied(name):
                        apps.append(InstalledApplication(name, str(item), "start_menu", kind))
        return apps

    def _is_denied(self, value: str) -> bool:
        normalized = self._normalize(value)
        return any(fragment in normalized for fragment in self.denied_name_fragments)

    def _normalize(self, value: str) -> str:
        return " ".join(str(value).strip().lower().replace("_", " ").replace("-", " ").split())
