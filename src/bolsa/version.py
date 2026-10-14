from __future__ import annotations

__version__ = "0.3.0.dev0"


def version_label(stage: str) -> str:
    """Devolve o rótulo de versão apresentado na interface."""
    return f"V{__version__} — {stage}"
