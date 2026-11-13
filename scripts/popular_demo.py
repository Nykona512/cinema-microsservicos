"""Popula o sistema via HTTP (sem acessar os bancos de outros serviços)."""
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

FILMES = os.getenv("FILMES_URL", "http://127.0.0.1:5001").rstrip("/")
SALAS = os.getenv("SALAS_URL", "http://127.0.0.1:5002").rstrip("/")
SESSOES = os.getenv("SESSOES_URL", "http://127.0.0.1:5003").rstrip("/")
VENDAS = os.getenv("VENDAS_URL", "http://127.0.0.1:5004").rstrip("/")
TIMEOUT = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))


def post(base, rota, dados):
    r = requests.post(f"{base}{rota}", json=dados, timeout=TIMEOUT)
    r.raise_for_status()
    print(f"{rota}: {r.json()}")
    return r.json()


def main():
    filme = post(FILMES, "/filmes", {"titulo": "Interestelar", "duracaoMinutos": 169})
    sala = post(SALAS, "/salas", {"nome": "Sala Demonstração", "capacidade": 20})
    inicio = (datetime.now(ZoneInfo(os.getenv("CINEMA_TIMEZONE", "America/Sao_Paulo"))).replace(tzinfo=None) + timedelta(days=30)).replace(hour=14, minute=0, second=0, microsecond=0)
    sessao = post(SESSOES, "/sessoes", {"filmeId": filme["id"], "salaId": sala["id"],
                                        "inicio": inicio.isoformat(), "precoInteira": 30.00})
    post(VENDAS, "/pedidos", {"sessaoId": sessao["id"],
                               "ingressos": [{"tipo": "INTEIRA"}, {"tipo": "MEIA"}]})
    print("Demo pronta! Consulte", f"{SESSOES}/sessoes/{sessao['id']}")


if __name__ == "__main__":
    main()
