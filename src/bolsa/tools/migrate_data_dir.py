from __future__ import annotations

import argparse
from pathlib import Path

from bolsa.config import load_config
from bolsa.infrastructure.database import (
    DataLocationError,
    build_data_location_migration_plan,
    execute_data_location_migration,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Migra explicitamente a base SQLite antiga do repositório para a "
            "localização de dados do utilizador."
        )
    )
    parser.add_argument(
        "--source",
        type=Path,
        help="Base SQLite de origem. Se omitido, usa data/bolsanext.sqlite3 do repositório.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Executa a migração. Sem este switch apenas mostra o plano.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirma sem pergunta interativa. Só tem efeito com --execute.",
    )
    return parser


def _print_plan(plan) -> None:
    print("Plano de migração de dados do BolsaNext")
    print()
    print(f"Origem : {plan.source}")
    print(f"Destino: {plan.destination}")
    print(f"Backup : {plan.backup}")
    print()
    print(
        "Origem existe : "
        + ("sim" if plan.source.is_file() else "não")
    )
    print(
        "Destino existe: "
        + ("sim" if plan.destination.exists() else "não")
    )
    print(
        "Backup existe : "
        + ("sim" if plan.backup.exists() else "não")
    )


def main() -> int:
    args = _build_parser().parse_args()
    config = load_config()
    plan = build_data_location_migration_plan(
        config,
        source=args.source,
    )

    _print_plan(plan)

    if not args.execute:
        print()
        print("Nenhuma alteração foi efetuada.")
        print(
            "Depois de confirmares os caminhos, executa novamente com --execute."
        )
        return 0

    if not args.yes:
        print()
        answer = input("Executar esta migração? [s/N] ").strip().lower()
        if answer not in {"s", "sim", "y", "yes"}:
            print("Migração cancelada. Nenhum dado foi alterado.")
            return 1

    try:
        result = execute_data_location_migration(plan)
    except (DataLocationError, FileExistsError, OSError) as exc:
        print()
        print(f"ERRO: {exc}")
        print("A base de origem não foi apagada.")
        return 2

    print()
    print("Migração concluída e validada.")
    print(f"Origem preservada: {result.source}")
    print(f"Backup criado    : {result.backup}")
    print(f"Base ativa nova  : {result.destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
