"""Treina o Prophet com o histórico USD/BRL do BCB e exporta os resultados."""

import argparse
import csv
import hashlib
import json
import math
from importlib.metadata import version
from pathlib import Path

import pandas as pd
from prophet import Prophet
from prophet.serialize import model_from_json, model_to_json


def carregar_csv(caminho: Path) -> pd.DataFrame:
    bruto = pd.read_csv(caminho)
    esperadas = {"data", "cotacao_brl_por_usd"}
    if set(bruto.columns) != esperadas:
        raise ValueError(f"O CSV precisa ter exatamente as colunas {sorted(esperadas)}")

    dados = bruto.rename(columns={"data": "ds", "cotacao_brl_por_usd": "y"})
    dados["ds"] = pd.to_datetime(dados["ds"], format="%Y-%m-%d", errors="raise")
    dados["y"] = pd.to_numeric(dados["y"], errors="raise")
    if len(dados) < 100 or dados.isna().any().any():
        raise ValueError("A base precisa ter pelo menos 100 linhas, sem valores vazios")
    if dados["ds"].duplicated().any() or (dados["y"] <= 0).any():
        raise ValueError("Há datas repetidas ou cotações não positivas")
    if not dados["ds"].is_monotonic_increasing:
        raise ValueError("As datas do CSV precisam estar em ordem crescente")
    return dados


def novo_modelo() -> Prophet:
    return Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.80,
    )


def calcular_metricas(real: pd.Series, previsto: pd.Series) -> dict[str, float]:
    erros = real.to_numpy() - previsto.to_numpy()
    return {
        "mae": round(float(abs(erros).mean()), 6),
        "rmse": round(float(math.sqrt((erros**2).mean())), 6),
    }


def gravar_json(caminho: Path, dados: dict) -> None:
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dados", type=Path, default=Path("dados/usd_brl_historico.csv"))
    parser.add_argument("--saida", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    args.saida.mkdir(parents=True, exist_ok=True)

    dados = carregar_csv(args.dados)
    quantidade_teste = round(len(dados) * 0.20)
    treino = dados.iloc[:-quantidade_teste].copy()
    teste = dados.iloc[-quantidade_teste:].copy()
    if treino["ds"].max() >= teste["ds"].min():
        raise ValueError("A separação temporal falhou")

    modelo_validacao = novo_modelo()
    modelo_validacao.fit(treino)
    previsoes = modelo_validacao.predict(teste[["ds"]])
    estimado = pd.Series(previsoes["yhat"].to_numpy(), index=teste.index)
    base_simples = pd.Series(float(treino["y"].iloc[-1]), index=teste.index)

    metricas = {
        "tipo_de_dados": "historicos",
        "fonte_dados": "Banco Central do Brasil, SGS 1, dolar comercial venda",
        "fonte_url": "https://dadosabertos.bcb.gov.br/dataset/1-taxa-de-cambio---livre---dolar-americano-venda---diario",
        "csv_sha256": hashlib.sha256(args.dados.read_bytes()).hexdigest(),
        "biblioteca_prophet": version("prophet"),
        "total_linhas": len(dados),
        "linhas_treino": len(treino),
        "linhas_teste": len(teste),
        "periodo_treino": [treino["ds"].iloc[0].date().isoformat(), treino["ds"].iloc[-1].date().isoformat()],
        "periodo_teste": [teste["ds"].iloc[0].date().isoformat(), teste["ds"].iloc[-1].date().isoformat()],
        "avaliacao": "previsao de todo o bloco de teste a partir do fim do treino",
        "prophet": calcular_metricas(teste["y"], estimado),
        "referencia_ultima_cotacao_do_treino": calcular_metricas(teste["y"], base_simples),
        "unidade": "BRL por USD",
    }
    gravar_json(args.saida / "metricas.json", metricas)

    with (args.saida / "previsoes_validacao.csv").open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo, lineterminator="\n")
        escritor.writerow(["data", "valor_observado", "previsao_prophet", "referencia_ultima_cotacao"])
        for data, real, pred, base in zip(teste["ds"], teste["y"], estimado, base_simples):
            escritor.writerow([data.date().isoformat(), f"{real:.4f}", f"{pred:.4f}", f"{base:.4f}"])

    modelo_final = novo_modelo()
    modelo_final.fit(dados)
    texto_modelo = model_to_json(modelo_final)
    (args.saida / "model.json").write_text(texto_modelo, encoding="utf-8")

    # Confere que o mesmo formato poderá ser carregado no backend.
    modelo_recarregado = model_from_json(texto_modelo)
    proxima_data = dados["ds"].iloc[-1] + pd.offsets.BDay(1)
    proxima = modelo_recarregado.predict(pd.DataFrame({"ds": [proxima_data]})).iloc[0]
    gravar_json(
        args.saida / "previsao_exemplo.json",
        {
            "data": proxima_data.date().isoformat(),
            "previsao_brl_por_usd": round(float(proxima["yhat"]), 4),
            "limite_inferior": round(float(proxima["yhat_lower"]), 4),
            "limite_superior": round(float(proxima["yhat_upper"]), 4),
            "tipo_de_dados": "historicos; BCB/SGS 1",
            "aviso": "demonstracao tecnica; nao e cotacao ou recomendacao financeira",
        },
    )

    print(json.dumps(metricas, ensure_ascii=False, indent=2))
    print(f"Modelo salvo em {args.saida / 'model.json'}")
    print(f"Próxima data de segunda a sexta: {proxima_data.date().isoformat()}")


if __name__ == "__main__":
    main()
