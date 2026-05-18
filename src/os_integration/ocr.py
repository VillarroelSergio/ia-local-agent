"""Local OCR provider abstraction and first local providers."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

try:
    from PIL import ImageOps
except ImportError:
    ImageOps = None

from .models import OCRBox, OCRResult, Rect, ScreenshotRequest
from .screenshots import ScreenshotService
from .security import OSScope, OSSecurityPolicy


class OCRProvider(ABC):
    name: str

    @abstractmethod
    def recognize(self, image, *, language: str = "eng") -> OCRResult:
        raise NotImplementedError


class ImagePreprocessor:
    def preprocess(
        self,
        image,
        *,
        grayscale: bool = True,
        threshold: bool = False,
        upscale: float = 1.0,
    ):
        if ImageOps is None:
            raise RuntimeError("Pillow no esta instalado; OCR requiere pillow para preprocesado.")
        processed = image.convert("RGB")
        if upscale and upscale != 1.0:
            processed = processed.resize((int(processed.width * upscale), int(processed.height * upscale)))
        if grayscale:
            processed = ImageOps.grayscale(processed)
        if threshold:
            processed = processed.point(lambda value: 255 if value > 170 else 0)
        return processed


class TesseractProvider(OCRProvider):
    name = "tesseract"

    def __init__(self):
        try:
            import pytesseract
        except ImportError as error:
            raise RuntimeError("pytesseract no esta instalado.") from error
        self._pytesseract = pytesseract

    def recognize(self, image, *, language: str = "eng") -> OCRResult:
        started = time.monotonic()
        data = self._pytesseract.image_to_data(image, lang=language, output_type=self._pytesseract.Output.DICT)
        boxes: list[OCRBox] = []
        words: list[str] = []
        for index, text in enumerate(data.get("text", [])):
            cleaned = (text or "").strip()
            if not cleaned:
                continue
            try:
                confidence = float(data["conf"][index])
            except (ValueError, TypeError):
                confidence = -1.0
            rect = Rect(
                int(data["left"][index]),
                int(data["top"][index]),
                int(data["width"][index]),
                int(data["height"][index]),
            )
            boxes.append(OCRBox(cleaned, confidence, rect))
            words.append(cleaned)
        return OCRResult(
            text=" ".join(words),
            boxes=tuple(boxes),
            provider=self.name,
            language=language,
            duration_ms=int((time.monotonic() - started) * 1000),
        )


class PaddleProvider(OCRProvider):
    name = "paddleocr"

    def __init__(self):
        raise RuntimeError("PaddleOCR provider preparado, dependencia no instalada.")


class EasyOCRProvider(OCRProvider):
    name = "easyocr"

    def __init__(self):
        raise RuntimeError("EasyOCR provider preparado, dependencia no instalada.")


class OCRService:
    def __init__(
        self,
        *,
        provider: OCRProvider | None = None,
        screenshot_service: ScreenshotService | None = None,
        security: OSSecurityPolicy | None = None,
        preprocessor: ImagePreprocessor | None = None,
    ):
        self.security = security or OSSecurityPolicy()
        self.screenshot_service = screenshot_service or ScreenshotService(security=self.security)
        self.preprocessor = preprocessor or ImagePreprocessor()
        self.provider = provider or self._default_provider()

    def read_image(
        self,
        image,
        *,
        language: str = "eng",
        grayscale: bool = True,
        threshold: bool = False,
        upscale: float = 1.0,
    ) -> OCRResult:
        decision = self.security.evaluate_scope(OSScope.OCR_READ)
        if not decision.allowed:
            raise PermissionError(decision.reason)
        processed = self.preprocessor.preprocess(image, grayscale=grayscale, threshold=threshold, upscale=upscale)
        return self.provider.recognize(processed, language=language)

    def read_screen(self, request: ScreenshotRequest | None = None, *, language: str = "eng") -> OCRResult:
        screenshot = self.screenshot_service.capture(request)
        return self.read_image(screenshot.image, language=language)

    def _default_provider(self) -> OCRProvider:
        try:
            return TesseractProvider()
        except RuntimeError:
            return NullOCRProvider()


class NullOCRProvider(OCRProvider):
    name = "none"

    def recognize(self, image, *, language: str = "eng") -> OCRResult:
        return OCRResult(
            text="",
            boxes=(),
            provider=self.name,
            language=language,
            duration_ms=0,
            metadata={"error": "No hay provider OCR instalado. Instala pytesseract, paddleocr o easyocr."},
        )
