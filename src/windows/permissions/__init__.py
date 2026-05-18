try:
    from os_integration.security import OSDecision, OSScope, OSSecurityPolicy, TrustLevel
except ModuleNotFoundError:
    from src.os_integration.security import OSDecision, OSScope, OSSecurityPolicy, TrustLevel

PermissionsManager = OSSecurityPolicy

__all__ = ["OSDecision", "OSScope", "OSSecurityPolicy", "PermissionsManager", "TrustLevel"]
