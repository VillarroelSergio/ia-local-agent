"""Result verification for Computer Use steps and goals."""

from __future__ import annotations

import re

try:
    from computer_use.models import DesktopObservation, PlanStep
except ModuleNotFoundError:
    from src.computer_use.models import DesktopObservation, PlanStep


class ResultVerifier:
    def __init__(self, *, max_retries: int = 1, backoff_seconds: float = 0.2):
        self.max_retries = max(0, max_retries)
        self.backoff_seconds = max(0.0, backoff_seconds)

    def verify_step(self, step: PlanStep, observation: DesktopObservation, result: dict | None = None) -> dict:
        expected = step.expected or {}
        if "text_contains" in expected:
            return self.verify_text(observation, expected["text_contains"])
        if "control_exists" in expected:
            return self.verify_control_exists(observation, expected["control_exists"])
        if step.capability == "focus_window" and result and result.get("ok") is False:
            return {"ok": False, "reason": result.get("error", "focus failed")}
        if result and result.get("ok") is False:
            return {"ok": False, "reason": result.get("error", "La ejecucion del paso fallo.")}
        return {"ok": True, "reason": "Sin expectativa explicita; paso aceptado si ejecucion no fallo."}

    def verify_goal(self, goal: str, observation: DesktopObservation) -> dict:
        if not goal.strip():
            return {"ok": False, "reason": "Objetivo vacio."}
        normalized = goal.lower()
        if any(token in normalized for token in ("escribe", "introduce")):
            match = re.search(r"[\"'](?P<text>.+?)[\"']", goal)
            if not match:
                return {"ok": False, "reason": "No se pudo identificar el texto esperado."}
            return self.verify_text(observation, match.group("text"))
        if any(token in normalized for token in ("texto", "leer", "extract")):
            return {
                "ok": bool(observation.visible_text.strip()),
                "reason": "Texto visible extraido." if observation.visible_text.strip() else "No se encontro texto visible.",
            }
        if any(token in normalized for token in ("observa", "analiza", "resume", "estado")):
            return {
                "ok": not observation.blocked_by_policy,
                "reason": "Estado del escritorio observado." if not observation.blocked_by_policy else "Observacion bloqueada por politica.",
            }
        return {"ok": False, "reason": "El objetivo no tiene un criterio de verificacion soportado."}

    def verify_window(self, observation: DesktopObservation, query: str) -> dict:
        window = observation.active_window
        haystack = " ".join(part for part in (window.title, window.process_name) if part) if window else ""
        ok = query.lower() in haystack.lower()
        return {"ok": ok, "reason": "Ventana coincide." if ok else "Ventana activa no coincide."}

    def verify_text(self, observation: DesktopObservation, expected_text: str) -> dict:
        ok = expected_text.lower() in observation.visible_text.lower()
        return {"ok": ok, "reason": "Texto encontrado." if ok else "Texto esperado no encontrado."}

    def verify_control_exists(self, observation: DesktopObservation, name: str) -> dict:
        needle = name.lower()
        ok = any(needle in control.name.lower() for control in observation.controls)
        return {"ok": ok, "reason": "Control encontrado." if ok else "Control no encontrado."}
