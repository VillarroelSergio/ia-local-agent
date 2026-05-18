try:
    from os_integration.security import OSSecurityPolicy
except ModuleNotFoundError:
    from src.os_integration.security import OSSecurityPolicy

__all__ = ["OSSecurityPolicy"]
