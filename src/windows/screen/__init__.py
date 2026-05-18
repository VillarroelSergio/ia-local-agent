try:
    from os_integration.models import CaptureTarget, ScreenshotRequest, ScreenshotResult
    from os_integration.screenshots import RateLimiter, ScreenshotService
except ModuleNotFoundError:
    from src.os_integration.models import CaptureTarget, ScreenshotRequest, ScreenshotResult
    from src.os_integration.screenshots import RateLimiter, ScreenshotService

ScreenService = ScreenshotService

__all__ = ["CaptureTarget", "RateLimiter", "ScreenService", "ScreenshotRequest", "ScreenshotResult", "ScreenshotService"]
