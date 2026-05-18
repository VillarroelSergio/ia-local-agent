"""Schemas Pydantic reutilizables para tools locales."""

from pydantic import BaseModel, ConfigDict, Field


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OpenApplicationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_name: str = Field(
        ...,
        max_length=120,
        description="Nombre de una aplicacion instalada, por ejemplo notepad, chrome, vscode o calculator.",
    )


class LimitInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=15, ge=1, le=50, description="Numero maximo de elementos.")


class DirectoryListInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(default=".", description="Carpeta a listar.")
    limit: int = Field(default=50, ge=1, le=100, description="Maximo 100 elementos.")


class ReadTextFileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(..., description="Archivo de texto UTF-8 a leer.")
    max_chars: int = Field(default=12000, ge=1, le=12000, description="Caracteres maximos.")


class SearchFilesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(..., description="Carpeta donde buscar.")
    pattern: str = Field(..., description="Patron glob simple, por ejemplo *.py o *.pdf.")
    limit: int = Field(default=20, ge=1, le=100, description="Numero maximo de resultados.")


class SetClipboardInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., max_length=8000, description="Texto a copiar al portapapeles.")


class MoveMouseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: int = Field(..., ge=0, le=10000, description="Coordenada X.")
    y: int = Field(..., ge=0, le=10000, description="Coordenada Y.")
    duration: float = Field(default=0.2, ge=0, le=3, description="Duracion del movimiento en segundos.")


class ClickMouseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    button: str = Field(default="left", description="Boton: left, right o middle.")
    clicks: int = Field(default=1, ge=1, le=3, description="Numero de clicks.")


class PressKeyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., description="Nombre de tecla pyautogui, por ejemplo enter, esc o tab.")


class HotkeyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keys: list[str] = Field(..., min_length=1, max_length=5, description="Lista de teclas, por ejemplo ['ctrl', 'c'].")


class TypeTextInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., max_length=500, description="Texto a escribir con teclado.")
    interval: float = Field(default=0.02, ge=0, le=0.5, description="Pausa entre caracteres.")


class OpenUrlInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(..., description="URL http:// o https://.")


class PowerShellInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: str = Field(..., max_length=300, description="Comando PowerShell permitido de solo inspeccion.")
    timeout: int = Field(default=10, ge=1, le=15, description="Timeout maximo en segundos.")
