"""Providers LLM desacoplados del orquestador del agente."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from time import monotonic, sleep

from openai import OpenAI


@dataclass
class LLMRequest:
    """Peticion normalizada para cualquier provider."""

    messages: list
    model: str | None = None
    temperature: float = 0.7
    tools: list | None = None
    tool_choice: str | None = None
    stream: bool = True
    metadata: dict = field(default_factory=dict)


@dataclass
class ProviderMetrics:
    """Metricas basicas de una llamada a provider."""

    provider: str
    model: str
    latency_ms: int
    ok: bool
    error: str | None = None


class ProviderError(RuntimeError):
    """Error normalizado al hablar con un provider LLM."""


class LLMProvider(ABC):
    """Contrato base para providers de modelos."""

    name: str

    @abstractmethod
    def stream(self, request: LLMRequest):
        """Devuelve chunks en streaming."""

    @abstractmethod
    def list_models(self):
        """Devuelve los modelos disponibles cuando el provider lo soporte."""

    @abstractmethod
    def healthcheck(self):
        """Comprueba si el provider esta disponible."""


class LMStudioProvider(LLMProvider):
    """Provider para LM Studio mediante API OpenAI-compatible."""

    name = "lmstudio"

    def __init__(self, base_url, api_key, default_model, retries=1, retry_delay=0.4):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.default_model = default_model
        self.retries = retries
        self.retry_delay = retry_delay
        self.last_metrics = None

    def stream(self, request):
        model = request.model or self.default_model
        started_at = monotonic()
        last_error = None
        messages = self.prepare_messages(request.messages)

        for attempt in range(self.retries + 1):
            try:
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": request.temperature,
                    "stream": True,
                }

                if request.tools:
                    payload["tools"] = request.tools

                if request.tool_choice:
                    payload["tool_choice"] = request.tool_choice

                stream = self.client.chat.completions.create(**payload)
                self.last_metrics = ProviderMetrics(
                    provider=self.name,
                    model=model,
                    latency_ms=int((monotonic() - started_at) * 1000),
                    ok=True,
                )
                return stream
            except Exception as error:
                last_error = error

                if attempt < self.retries:
                    sleep(self.retry_delay)

        self.last_metrics = ProviderMetrics(
            provider=self.name,
            model=model,
            latency_ms=int((monotonic() - started_at) * 1000),
            ok=False,
            error=str(last_error),
        )
        raise ProviderError(f"Fallo provider {self.name}: {last_error}") from last_error

    def prepare_messages(self, messages):
        """Normaliza mensajes para plantillas Jinja estrictas de LM Studio.

        Algunos modelos locales fallan si no encuentran un mensaje ``user`` o
        si el historial termina en roles que su template no entiende. La capa
        OpenAI-compatible acepta mas variantes que muchos chat templates.
        """
        prepared = []

        for message in messages or []:
            role = message.get("role", "user")
            content = message.get("content") or ""

            if role == "tool":
                role = "user"
                name = message.get("name") or "tool"
                content = f"Resultado de la herramienta {name}:\n{content}"

            if role not in {"system", "user", "assistant"}:
                role = "user"

            if not content.strip() and role != "assistant":
                continue

            prepared.append({"role": role, "content": content})

        if not any(message["role"] == "user" for message in prepared):
            prepared.append({
                "role": "user",
                "content": "Continua la conversacion con la informacion disponible.",
            })

        while prepared and prepared[-1]["role"] == "assistant":
            prepared.pop()

        if not prepared or not any(message["role"] == "user" for message in prepared):
            prepared.append({
                "role": "user",
                "content": "Continua la conversacion con la informacion disponible.",
            })

        return prepared

    def list_models(self):
        try:
            return self.client.models.list()
        except Exception as error:
            raise ProviderError(f"No se pudieron listar modelos: {error}") from error

    def healthcheck(self):
        try:
            self.list_models()
            return True
        except ProviderError:
            return False


class ProviderRegistry:
    """Registro de providers disponibles."""

    def __init__(self):
        self._providers = {}

    def register(self, provider):
        self._providers[provider.name] = provider

    def get(self, name):
        provider = self._providers.get(name)

        if provider is None:
            available = ", ".join(sorted(self._providers))
            raise ProviderError(f"Provider no registrado: {name}. Disponibles: {available}")

        return provider


def build_provider_registry(settings):
    registry = ProviderRegistry()
    registry.register(
        LMStudioProvider(
            base_url=settings.lmstudio_base_url,
            api_key=settings.lmstudio_api_key,
            default_model=settings.default_model,
        )
    )
    return registry
