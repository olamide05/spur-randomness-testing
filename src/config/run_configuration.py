"""Presentation helpers for recording the effective STS test settings."""

from typing import Any


def _value(test_config: Any, field: str, default: Any) -> Any:
    """Read a field from either a TestConfig or the UI's plain dictionary."""
    if isinstance(test_config, dict):
        return test_config.get(field, default)
    return getattr(test_config, field, default)


def effective_test_settings(config, defaults: dict) -> list[dict]:
    """Return enabled parameterized tests and the values used for a run.

    The returned default/value pair is deliberately kept together so reports
    can verify a custom setting (for example, 9 -> 10) without requiring the
    reader to know the STS defaults.
    """
    settings = []
    for test_name, parameters in defaults.items():
        test_config = getattr(config, "tests", {}).get(test_name)
        if not _value(test_config, "enabled", True):
            continue
        configured = _value(test_config, "parameters", {}) or {}
        for parameter, default in parameters.items():
            value = configured.get(parameter, default)
            settings.append({
                "test": test_name,
                "parameter": parameter,
                "default": default,
                "value": value,
                "custom": value != default,
            })
    return settings
