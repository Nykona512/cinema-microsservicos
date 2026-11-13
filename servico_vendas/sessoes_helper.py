import os
from comum.cliente_http import chamar


def base():
    return os.getenv("SESSOES_URL", "http://127.0.0.1:5003").rstrip("/")


def buscar_sessao(sessao_id):
    return chamar("GET", f"{base()}/sessoes/{sessao_id}")


def reservar(sessao_id, reserva_id, quantidade, meias):
    return chamar("POST", f"{base()}/sessoes/{sessao_id}/reservas",
                  {"reservaId": reserva_id, "quantidade": quantidade, "meias": meias})


def cancelar(sessao_id, reserva_id):
    return chamar("POST", f"{base()}/sessoes/{sessao_id}/reservas/{reserva_id}/cancelar")
