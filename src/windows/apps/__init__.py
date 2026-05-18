try:
    from os_integration.apps import ApplicationManager, InstalledApplication, LaunchResult
except ModuleNotFoundError:
    from src.os_integration.apps import ApplicationManager, InstalledApplication, LaunchResult

__all__ = ["ApplicationManager", "InstalledApplication", "LaunchResult"]
