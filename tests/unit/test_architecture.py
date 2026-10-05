from __future__ import annotations

import ast
from pathlib import Path


def test_application_does_not_import_infrastructure() -> None:
    root = Path(__file__).resolve().parents[2]
    app_dir = root / "src" / "bolsa" / "app"
    violations: list[str] = []

    for path in sorted(app_dir.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "bolsa.infrastructure" or alias.name.startswith(
                        "bolsa.infrastructure."
                    ):
                        violations.append(
                            f"{path.relative_to(root)}:{node.lineno} importa {alias.name}"
                        )

            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "bolsa.infrastructure" or module.startswith(
                    "bolsa.infrastructure."
                ):
                    violations.append(
                        f"{path.relative_to(root)}:{node.lineno} importa {module}"
                    )

    assert violations == [], (
        "A camada Application não pode depender de Infrastructure:\n"
        + "\n".join(violations)
    )
