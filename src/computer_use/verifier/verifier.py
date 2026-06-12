"""Result verification for Computer Use steps and goals."""

from __future__ import annotations

try:
    from computer_use.models import DesktopObservation, PlanStep
except ModuleNotFoundError:
    from src.computer_use.models import DesktopObservation, PlanStep


class ResultVerifier:
    def verify_step(self, step: PlanStep, observation: DesktopObservation, result: dict | None = None) -> dict:
        expected = step.expected or {}
        if "text_contains" in expected:
            return self.verify_text(observation, expected["text_contains"])
        if "control_exists" in expected:
            return self.verify_control_exists(observation, expected["control_exists"])
        if step.capability == "focus_window" and result and result.get("ok") is False:
            return {"ok": False, "reason": result.get("error", "focus failed")}
        return {"ok": True, "reason": "Sin expectativa explicita; paso aceptado si ejecucion no fallo."}

    def verify_goal(self, goal: str, observation: DesktopObservation) -> dict:
        if not goal.strip():
            return {"ok": False, "reason": "Objetivo vacio."}
        return {"ok": True, "reason": "Verificacion de objetivo pendiente de criterio especifico."}

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
