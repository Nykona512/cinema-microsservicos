"""HTTP síncrono entre serviços; timeout, falhas claras e URLs em ambiente."""
import os
import requests
from comum.api import ErroIntegracao


def chamar(metodo, url, dados=None):
    try:
        timeout = float(os.getenv("HTTP_TIMEOUT_SECONDS", "5"))
        resposta = requests.request(metodo, url, json=dados, timeout=timeout)
    except (requests.Timeout, requests.ConnectionError) as erro:
        raise ErroIntegracao(
            f"Integração indisponível ({metodo} {url}): tempo esgotado ou conexão falhou.",
            503, incerto=True,
        ) from erro
    except requests.RequestException as erro:
        raise ErroIntegracao(f"Falha de comunicação com outro serviço: {erro}", 503, incerto=True) from erro
    try:
        corpo = resposta.json()
    except ValueError:
        corpo = {}
    if not resposta.ok:
        mensagem = corpo.get("mensagem", "Erro ao consultar outro microsserviço.") if isinstance(corpo, dict) else "Erro ao consultar outro microsserviço."
        codigo = resposta.status_code if resposta.status_code in (400, 404, 409) else 503
        raise ErroIntegracao(mensagem, codigo, incerto=(codigo == 503))
    if not isinstance(corpo, dict):
        raise ErroIntegracao("Resposta JSON inesperada do outro microsserviço.", 503, incerto=True)
    return corpo
