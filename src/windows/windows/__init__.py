try:
    from os_integration.models import MonitorInfo, Rect, WindowInfo, WindowState
    from os_integration.windows import WindowManager
except ModuleNotFoundError:
    from src.os_integration.models import MonitorInfo, Rect, WindowInfo, WindowState
    from src.os_integration.windows import WindowManager

__all__ = ["MonitorInfo", "Rect", "WindowInfo", "WindowManager", "WindowState"]
