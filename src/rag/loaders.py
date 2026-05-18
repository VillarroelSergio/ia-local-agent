"""Loaders documentales para RAG local."""

from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path

from .models import RawDocument


TEXT_EXTENSIONS = {".txt", ".log"}
MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdx"}
JSON_EXTENSIONS = {".json"}
CSV_EXTENSIONS = {".csv"}
PDF_EXTENSIONS = {".pdf"}
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".cs", ".cpp", ".c", ".h",
    ".go", ".rs", ".php", ".rb", ".ps1", ".sql", ".html", ".css", ".xml",
    ".yaml", ".yml", ".toml",
}


class DocumentLoaderRegistry:
    """Selecciona loaders por extension."""

    def load(self, path: Path) -> RawDocument:
        suffix = path.suffix.lower()

        if suffix in MARKDOWN_EXTENSIONS:
            return self.load_text(path, "markdown")
        if suffix in TEXT_EXTENSIONS:
            return self.load_text(path, "text")
        if suffix in JSON_EXTENSIONS:
            return self.load_json(path)
        if suffix in CSV_EXTENSIONS:
            return self.load_csv(path)
        if suffix in PDF_EXTENSIONS:
            return self.load_pdf(path)
        if suffix in CODE_EXTENSIONS:
            return self.load_text(path, "code")

        raise ValueError(f"Tipo de archivo no soportado: {path.suffix}")

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in (
            TEXT_EXTENSIONS
            | MARKDOWN_EXTENSIONS
            | JSON_EXTENSIONS
            | CSV_EXTENSIONS
            | PDF_EXTENSIONS
            | CODE_EXTENSIONS
        )

    def load_text(self, path: Path, file_type: str) -> RawDocument:
        text = path.read_text(encoding="utf-8", errors="replace")
        return RawDocument(path=path, text=text, file_type=file_type)

    def load_json(self, path: Path) -> RawDocument:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        pretty = json.dumps(data, ensure_ascii=False, indent=2)
        return RawDocument(path=path, text=pretty, file_type="json")

    def load_csv(self, path: Path) -> RawDocument:
        raw = path.read_text(encoding="utf-8", errors="replace")
        reader = csv.reader(StringIO(raw))
        rows = list(reader)
        lines = []

        if rows:
            header = rows[0]
            lines.append("CSV columns: " + ", ".join(header))

            for index, row in enumerate(rows[1:], start=1):
                pairs = [
                    f"{column}={value}"
                    for column, value in zip(header, row)
                ]
                lines.append(f"row {index}: " + "; ".join(pairs))

        return RawDocument(path=path, text="\n".join(lines), file_type="csv")

    def load_pdf(self, path: Path) -> RawDocument:
        try:
            from pypdf import PdfReader
        except ImportError as error:
            raise RuntimeError(
                "Para indexar PDFs instala pypdf: pip install pypdf"
            ) from error

        reader = PdfReader(str(path))
        pages = []

        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append(f"\n\n[Page {index}]\n{text.strip()}")

        return RawDocument(
            path=path,
            text="\n".join(pages),
            file_type="pdf",
            metadata={"page_count": len(reader.pages)},
        )
