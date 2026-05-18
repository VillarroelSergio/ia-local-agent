try:
    from os_integration.automation import AutomationEngine, RetryPolicy, StepResult
except ModuleNotFoundError:
    from src.os_integration.automation import AutomationEngine, RetryPolicy, StepResult

__all__ = ["AutomationEngine", "RetryPolicy", "StepResult"]
