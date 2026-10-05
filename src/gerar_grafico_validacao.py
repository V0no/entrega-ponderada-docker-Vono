"""Plota a validação cronológica do Prophet contra a referência simples."""

import argparse
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-ponderada")

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--previsoes", type=Path, default=Path("artifacts/previsoes_validacao.csv")
    )
    parser.add_argument("--saida", type=Path, default=Path("docs/grafico-validacao.png"))
    args = parser.parse_args()

    dados = pd.read_csv(args.previsoes, parse_dates=["data"])
    fig, ax = plt.subplots(figsize=(13, 5.5), dpi=190)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f8fafc")
    ax.plot(dados["data"], dados["valor_observado"], label="BCB: cotação observada", color="#1f2937", linewidth=1.9)
    ax.plot(dados["data"], dados["previsao_prophet"], label="Previsão Prophet", color="#2563eb", linewidth=2.1)
    ax.plot(dados["data"], dados["referencia_ultima_cotacao"], label="Último valor do treino", color="#d97706", linewidth=1.7, linestyle="--")
    ax.set_title("USD/BRL: validação em dados históricos do BCB", loc="left", fontsize=16, fontweight="bold", pad=18)
    ax.set_ylabel("BRL por USD")
    ax.set_xlabel("Período de teste: 31/12/2025 a 30/09/2026")
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
    ax.grid(axis="y", color="#d6dee8", linewidth=0.9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper right", frameon=True, facecolor="white", framealpha=0.96)
    fig.tight_layout()
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.saida, facecolor="white", bbox_inches="tight")
    print(args.saida)


if __name__ == "__main__":
    main()
