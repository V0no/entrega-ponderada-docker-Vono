"""API HTTP simples que carrega o modelo Prophet e responde previsões USD/BRL."""

import json
import os
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pandas as pd
from prophet.serialize import model_from_json


MODEL_PATH = Path(os.getenv("MODEL_PATH", "/app/artifacts/model.json"))
PORT = int(os.getenv("PORT", "8000"))
modelo = model_from_json(MODEL_PATH.read_text(encoding="utf-8"))
ultima_data_treino = pd.Timestamp(modelo.history["ds"].max()).date()


class Handler(BaseHTTPRequestHandler):
    def responder(self, status: int, conteudo: dict) -> None:
        corpo = json.dumps(conteudo, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self) -> None:
        if self.path != "/health":
            self.responder(404, {"erro": "rota não encontrada"})
            return
        self.responder(200, {"status": "ok", "modelo_carregado": True, "ultima_data_treino": ultima_data_treino.isoformat()})

    def do_POST(self) -> None:
        if self.path != "/predict":
            self.responder(404, {"erro": "rota não encontrada"})
            return
        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
            if tamanho <= 0 or tamanho > 8192:
                raise ValueError("corpo vazio ou grande demais")
            pedido = json.loads(self.rfile.read(tamanho))
            if not isinstance(pedido, dict) or not isinstance(pedido.get("data"), str):
                raise ValueError("envie um JSON com a chave 'data' no formato AAAA-MM-DD")
            data_alvo = date.fromisoformat(pedido["data"])
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as erro:
            self.responder(400, {"erro": str(erro)})
            return

        if data_alvo <= ultima_data_treino:
            self.responder(422, {"erro": "a data deve ser posterior ao fim do treino", "ultima_data_treino": ultima_data_treino.isoformat()})
            return
        if data_alvo.weekday() >= 5:
            self.responder(422, {"erro": "use uma data de segunda a sexta; feriados não são tratados"})
            return

        previsao = modelo.predict(pd.DataFrame({"ds": [pd.Timestamp(data_alvo)]})).iloc[0]
        self.responder(
            200,
            {
                "data": data_alvo.isoformat(),
                "previsao_brl_por_usd": round(float(previsao["yhat"]), 4),
                "limite_inferior": round(float(previsao["yhat_lower"]), 4),
                "limite_superior": round(float(previsao["yhat_upper"]), 4),
                "unidade": "BRL por USD",
                "dados": "histórico BCB/SGS 1; previsão experimental",
            },
        )


if __name__ == "__main__":
    servidor = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"API pronta na porta {PORT}; modelo treinado até {ultima_data_treino}", flush=True)
    servidor.serve_forever()
