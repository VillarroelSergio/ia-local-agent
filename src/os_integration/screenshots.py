"""Screenshot capture service with throttling and temporary cache."""

from __future__ import annotations

import io
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageGrab
except ImportError:
    Image = None
    ImageGrab = None

from .models import CaptureTarget, MonitorInfo, Rect, ScreenshotRequest, ScreenshotResult
from .security import OSScope, OSSecurityPolicy
from .windows import WindowManager

try:
    import mss
except ImportError:
    mss = None


class RateLimiter:
    def __init__(self, *, min_interval_ms: int = 150):
        self.min_interval_ms = min_interval_ms
        self._last_call = 0.0

    def allow(self) -> bool:
        now = time.monotonic()
        if (now - self._last_call) * 1000 < self.min_interval_ms:
            return False
        self._last_call = now
        return True


class ScreenshotService:
    """Captures screen images through mss when available, with PIL fallback."""

    def __init__(
        self,
        *,
        window_manager: WindowManager | None = None,
        security: OSSecurityPolicy | None = None,
        rate_limiter: RateLimiter | None = None,
    ):
        self.security = security or OSSecurityPolicy()
        self.window_manager = window_manager or WindowManager(security=self.security)
        self.rate_limiter = rate_limiter or RateLimiter()
        self._cache: dict[str, tuple[float, ScreenshotResult]] = {}

    def capture(self, request: ScreenshotRequest | None = None) -> ScreenshotResult:
        request = request or ScreenshotRequest()
        cache_key = self._cache_key(request)
        cached = self._get_cached(cache_key, request.max_age_ms)
        if cached:
            return replace(cached, cached=True)

        if not self.rate_limiter.allow():
            cached = self._get_cached(cache_key, max(request.max_age_ms, self.rate_limiter.min_interval_ms))
            if cached:
                return replace(cached, cached=True, metadata={**cached.metadata, "throttled": True})

        active_window = None
        if request.target == CaptureTarget.ACTIVE_WINDOW:
            active_window = self.window_manager.get_window_info(request.window_handle) if request.window_handle else self.window_manager.get_active_window()

        decision = self.security.evaluate_scope(OSScope.SCREEN_CAPTURE, active_window)
        if not decision.allowed:
            raise PermissionError(decision.reason)

        rect = self._resolve_rect(request, active_window)
        image = self._capture_rect(rect)

        path = None
        if request.compress:
            image = self._compress_image(image, request.quality)
        if request.save_path:
            path = Path(request.save_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            image.save(path)

        result = ScreenshotResult(
            image=image,
            target=request.target,
            rect=rect,
            monitors=self.window_manager.list_monitors(),
            path=path,
            metadata={"backend": "mss" if mss is not None else "PIL.ImageGrab"},
        )
        self._cache[cache_key] = (time.monotonic(), result)
        return result

    def _resolve_rect(self, request: ScreenshotRequest, active_window) -> Rect:
        monitors = self.window_manager.list_monitors()
        if request.target == CaptureTarget.REGION:
            if request.region is None:
                raise ValueError("region es obligatorio para capturar una region.")
            return request.region
        if request.target == CaptureTarget.MONITOR:
            index = request.monitor_index or 0
            if index < 0 or index >= len(monitors):
                raise ValueError(f"Monitor no disponible: {index}")
            return monitors[index].rect
        if request.target == CaptureTarget.ACTIVE_WINDOW:
            if active_window is None or active_window.rect is None:
                raise ValueError("No hay ventana activa capturable.")
            return active_window.rect
        if monitors:
            left = min(m.rect.left for m in monitors)
            top = min(m.rect.top for m in monitors)
            right = max(m.rect.right for m in monitors)
            bottom = max(m.rect.bottom for m in monitors)
            return Rect(left, top, right - left, bottom - top)
        image = ImageGrab.grab()
        return Rect(0, 0, image.width, image.height)

    def _capture_rect(self, rect: Rect):
        if mss is not None:
            if Image is None:
                raise RuntimeError("mss requiere pillow para construir imagenes PIL en esta implementacion.")
            with mss.mss() as sct:
                raw = sct.grab({"left": rect.left, "top": rect.top, "width": rect.width, "height": rect.height})
                return Image.frombytes("RGB", raw.size, raw.rgb)
        if ImageGrab is None:
            raise RuntimeError("No hay backend de captura instalado. Instala pillow o mss.")
        return ImageGrab.grab(bbox=rect.as_tuple())

    def _compress_image(self, image, quality: int):
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=max(1, min(quality, 95)), optimize=True)
        buffer.seek(0)
        return Image.open(buffer).copy()

    def _cache_key(self, request: ScreenshotRequest) -> str:
        region = request.region.as_tuple() if request.region else None
        return f"{request.target.value}:{request.monitor_index}:{request.window_handle}:{region}:{request.compress}:{request.quality}"

    def _get_cached(self, cache_key: str, max_age_ms: int) -> ScreenshotResult | None:
        cached = self._cache.get(cache_key)
        if not cached:
            return None
        captured_at, result = cached
        if (time.monotonic() - captured_at) * 1000 <= max_age_ms:
            return result
        return None
