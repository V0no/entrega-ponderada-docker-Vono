"""Baixa a série SGS 1 (dólar comercial, venda) do Banco Central em CSV."""

import argparse
import csv
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados"
INICIO = date(2023, 1, 2)
FIM = date(2026, 9, 30)


def baixar(inicio: date, fim: date) -> tuple[list[tuple[str, str]], str]:
    if inicio >= fim or (fim.year, fim.month, fim.day) > (
        inicio.year + 10,
        inicio.month,
        inicio.day,
    ):
        raise ValueError("informe um período crescente de no máximo 10 anos")

    parametros = urlencode(
        {
            "formato": "json",
            "dataInicial": inicio.strftime("%d/%m/%Y"),
            "dataFinal": fim.strftime("%d/%m/%Y"),
        }
    )
    url = f"{API}?{parametros}"
    requisicao = Request(url, headers={"User-Agent": "ponderada-usd-brl/1.0"})
    with urlopen(requisicao, timeout=45) as resposta:
        registros = json.load(resposta)

    if not isinstance(registros, list) or len(registros) < 100:
        raise ValueError("a API não retornou uma série histórica suficiente")

    linhas = []
    anterior = None
    for registro in registros:
        try:
            dia = datetime.strptime(registro["data"], "%d/%m/%Y").date()
            valor = Decimal(registro["valor"])
        except (KeyError, TypeError, ValueError, InvalidOperation) as erro:
            raise ValueError(f"registro inválido da API: {registro!r}") from erro

        if not inicio <= dia <= fim or dia.weekday() >= 5:
            raise ValueError(f"data fora do intervalo ou em fim de semana: {dia}")
        if anterior is not None and dia <= anterior:
            raise ValueError(f"data repetida ou fora de ordem: {dia}")
        if not valor.is_finite() or valor <= 0:
            raise ValueError(f"cotação inválida em {dia}: {valor}")
        linhas.append((dia.isoformat(), str(valor)))
        anterior = dia

    return linhas, url


def main() -> None:
    destino = Path(__file__).resolve().parent.parent / "dados" / "usd_brl_historico.csv"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inicio", type=date.fromisoformat, default=INICIO)
    parser.add_argument("--fim", type=date.fromisoformat, default=FIM)
    parser.add_argument("--saida", type=Path, default=destino)
    args = parser.parse_args()

    linhas, url = baixar(args.inicio, args.fim)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    temporario = args.saida.with_suffix(".tmp")
    with temporario.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo, lineterminator="\n")
        escritor.writerow(["data", "cotacao_brl_por_usd"])
        escritor.writerows(linhas)
    temporario.replace(args.saida)
    print(f"{len(linhas)} cotações: {linhas[0][0]} a {linhas[-1][0]}")
    print(f"Fonte: {url}")
    print(f"CSV: {args.saida}")


if __name__ == "__main__":
    main()
