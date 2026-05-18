try:
    from os_integration.ocr import ImagePreprocessor, NullOCRProvider, OCRProvider, OCRService, TesseractProvider
    from os_integration.models import OCRBox, OCRResult
except ModuleNotFoundError:
    from src.os_integration.ocr import ImagePreprocessor, NullOCRProvider, OCRProvider, OCRService, TesseractProvider
    from src.os_integration.models import OCRBox, OCRResult

__all__ = ["ImagePreprocessor", "NullOCRProvider", "OCRBox", "OCRProvider", "OCRResult", "OCRService", "TesseractProvider"]
