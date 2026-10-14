"""Run with python tests/compare_portfolio_branches.py FEATURE_REF.

Loads only reviewed domain files from a Git object into an isolated namespace;
never checks out branches, opens databases or calls network providers.
"""
import importlib.util
import subprocess
import sys
import types
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "unit"))
from test_portfolio_oracle import CASES, implemented_replay, rational_replay  # noqa: E402
from bolsa.domain.instruments import Instrument  # noqa: E402


def load_feature(ref):
    prefix = "comparison_feature"
    package = types.ModuleType(prefix)
    package.__path__ = []
    sys.modules[prefix] = package
    for name in ("money", "models", "ledger"):
        path = f"src/bolsa/domain/portfolio/{name}.py"
        source = subprocess.check_output(["git", "show", f"{ref}:{path}"], text=True)
        source = source.replace("bolsa.domain.portfolio", prefix)
        spec = importlib.util.spec_from_loader(f"{prefix}.{name}", loader=None)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module.__name__] = module
        exec(compile(source, f"{ref}:{path}", "exec"), module.__dict__)
    return tuple(sys.modules[f"{prefix}.{name}"] for name in ("money", "models", "ledger"))


def main(ref):
    money, models, ledger = load_feature(ref)
    for index, rows in enumerate(CASES):
        versions = []
        for offset, (kind, q, price, fee, fx) in enumerate(rows):
            transaction = models.Transaction(
                Instrument("ORACLE", currency="USD"), models.TransactionType(kind),
                date(2020, 1, 1) + timedelta(days=offset), Decimal(q),
                money.Money(Decimal(price), "USD", Decimal(fx)),
                money.Money(Decimal(fee), "EUR"),
            )
            versions.append(models.TransactionVersion(transaction))
        result = ledger.replay(models.Ledger(models.Portfolio("Synthetic", "EUR"), tuple(versions)))
        observed = result.positions[0]
        canonical = implemented_replay(rows)
        print(index, "rational", rational_replay(rows), "feature",
              (observed.quantity, observed.cost, observed.realized_pnl), "dev",
              (canonical.quantity, canonical.cost, canonical.realized_pnl))
    for label, function in (
        ("signed settlement", lambda: money.Money(Decimal("-4"), "EUR")),
        ("signed dividend net", lambda: money.Money(Decimal("-1"), "EUR")),
    ):
        try:
            function()
            print(label, "accepted")
        except ValueError as error:
            print(label, "rejected:", error)


if __name__ == "__main__":
    main(sys.argv[1])
