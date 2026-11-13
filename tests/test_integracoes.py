"""Testes end-to-end: sobem quatro processos Flask reais com bancos temporários."""
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]


def porta_livre():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def post(url, dados):
    return requests.post(url, json=dados, timeout=5)


def proxima_data(hora=14):
    return (datetime.now() + timedelta(days=30)).replace(
        hour=hora, minute=0, second=0, microsecond=0
    ).isoformat()


@pytest.fixture(scope="module")
def sistema(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("cinema_end_to_end")
    portas = {s: porta_livre() for s in ("filmes", "salas", "sessoes", "vendas")}
    urls = {s: f"http://127.0.0.1:{p}" for s, p in portas.items()}
    processos = []
    arquivos_logs = []
    try:
        for nome in ("filmes", "salas", "sessoes", "vendas"):
            env = os.environ.copy()
            env.update({
                "PORT": str(portas[nome]),
                "DATABASE_URL": f"sqlite:///{tmp / (nome + '.db')}",
                "FILMES_URL": urls["filmes"],
                "SALAS_URL": urls["salas"],
                "SESSOES_URL": urls["sessoes"],
                "HTTP_TIMEOUT_SECONDS": "3",
            })
            log = open(tmp / f"{nome}.log", "w", encoding="utf-8")
            arquivos_logs.append(log)
            processo = subprocess.Popen(
                [sys.executable, "-m", f"servico_{nome}.app"],
                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
            )
            processos.append(processo)
            for tentativa in range(150):
                if processo.poll() is not None:
                    raise RuntimeError(f"Serviço {nome} encerrou; leia {tmp / (nome + '.log')}")
                try:
                    r = requests.get(urls[nome] + "/health", timeout=0.25)
                    if r.status_code == 200:
                        break
                except requests.RequestException:
                    pass
                time.sleep(0.1)
            else:
                raise RuntimeError(f"Serviço {nome} não iniciou; leia {tmp / (nome + '.log')}")
        yield urls
    finally:
        for processo in reversed(processos):
            if processo.poll() is None:
                processo.terminate()
        for processo in processos:
            try:
                processo.wait(timeout=5)
            except subprocess.TimeoutExpired:
                processo.kill()
                processo.wait()
        for log in arquivos_logs:
            log.close()


def montar_sessao(urls, capacidade=20, hora=14):
    filme = post(urls["filmes"] + "/filmes",
                 {"titulo": "Interestelar", "duracaoMinutos": 169})
    assert filme.status_code == 201, filme.text
    sala = post(urls["salas"] + "/salas",
                {"nome": "Sala Teste", "capacidade": capacidade})
    assert sala.status_code == 201, sala.text
    corpo = {"filmeId": filme.json()["id"], "salaId": sala.json()["id"],
             "inicio": proxima_data(hora), "precoInteira": 30.0}
    sessao = post(urls["sessoes"] + "/sessoes", corpo)
    assert sessao.status_code == 201, sessao.text
    return corpo, sessao.json()["id"]


def test_compra_e_tres_integracoes(sistema):
    dados, sessao_id = montar_sessao(sistema)
    pedido = post(sistema["vendas"] + "/pedidos",
                  {"sessaoId": sessao_id,
                   "ingressos": [{"tipo": "INTEIRA"}, {"tipo": "MEIA"}]})
    assert pedido.status_code == 201, pedido.text
    assert pedido.json()["status"] == "CONFIRMADO"
    assert pedido.json()["valorTotal"] == 45.0
    assert len(pedido.json()["ingressos"]) == 2
    sessao = requests.get(sistema["sessoes"] + f"/sessoes/{sessao_id}", timeout=5).json()
    assert sessao["vagasDisponiveis"] == 18
    assert sessao["meiasDisponiveis"] == 7
    ingresso_id = pedido.json()["ingressos"][0]["id"]
    response = requests.get(sistema["vendas"] + f"/ingressos/{ingresso_id}", timeout=5)
    assert response.status_code == 200
    assert response.json()["sessaoId"] == sessao_id


def test_r2_impede_sobreposicao(sistema):
    dados, sessao_id = montar_sessao(sistema)
    dados["inicio"] = (datetime.fromisoformat(dados["inicio"]) + timedelta(hours=1)).isoformat()
    conflita = post(sistema["sessoes"] + "/sessoes", dados)
    assert conflita.status_code == 400
    assert "R2" in conflita.json()["mensagem"]
    dados["inicio"] = (datetime.fromisoformat(dados["inicio"]) + timedelta(hours=3)).isoformat()
    sem_conflito = post(sistema["sessoes"] + "/sessoes", dados)
    assert sem_conflito.status_code == 201, sem_conflito.text


def test_r1_limite_meia_e_compra_atomica(sistema):
    _, sessao_id = montar_sessao(sistema, capacidade=5)
    primeira = post(sistema["vendas"] + "/pedidos",
                    {"sessaoId": sessao_id,
                     "ingressos": [{"tipo": "MEIA"}, {"tipo": "MEIA"}]})
    assert primeira.status_code == 201, primeira.text
    assert primeira.json()["valorTotal"] == 30.0
    segunda = post(sistema["vendas"] + "/pedidos",
                   {"sessaoId": sessao_id, "ingressos": [{"tipo": "MEIA"}]})
    assert segunda.status_code == 400
    assert "R1" in segunda.json()["mensagem"]
    sessao = requests.get(sistema["sessoes"] + f"/sessoes/{sessao_id}", timeout=5).json()
    assert sessao["vagasDisponiveis"] == 3
    assert sessao["meiasDisponiveis"] == 0


def test_r3_limite_seis(sistema):
    _, sessao_id = montar_sessao(sistema)
    resposta = post(sistema["vendas"] + "/pedidos",
                    {"sessaoId": sessao_id, "ingressos": [{"tipo": "INTEIRA"}] * 7})
    assert resposta.status_code == 400
    assert "R3" in resposta.json()["mensagem"]


def test_reserva_idempotente_e_compensacao_tardia(sistema):
    _, sessao_id = montar_sessao(sistema, capacidade=5)
    reserva_id = str(uuid4())
    rota = sistema["sessoes"] + f"/sessoes/{sessao_id}/reservas"
    dados = {"reservaId": reserva_id, "quantidade": 2, "meias": 1}
    assert post(rota, dados).status_code == 201
    repetida = post(rota, dados)
    assert repetida.status_code == 201
    assert repetida.json()["repetida"] is True
    cancelar_rota = rota + f"/{reserva_id}/cancelar"
    assert post(cancelar_rota, {}).status_code == 200
    assert post(cancelar_rota, {}).status_code == 200
    sessao = requests.get(sistema["sessoes"] + f"/sessoes/{sessao_id}", timeout=5).json()
    assert sessao["vagasDisponiveis"] == 5
    assert sessao["meiasDisponiveis"] == 2
    # Cancelamento recebido antes da reserva gera tombstone.
    outro_uuid = str(uuid4())
    assert post(rota + f"/{outro_uuid}/cancelar", {}).status_code == 200
    tardia = post(rota, {"reservaId": outro_uuid, "quantidade": 1, "meias": 0})
    assert tardia.status_code == 409


def test_servico_indisponivel_responde_erro_claro(tmp_path):
    """O HTTP de um serviço fora do ar não deve derrubar a API de Vendas."""
    porta = porta_livre()
    servico_inexistente = porta_livre()
    env = os.environ.copy()
    env.update({"PORT": str(porta), "DATABASE_URL": f"sqlite:///{tmp_path / 'vendas_isolado.db'}",
                "SESSOES_URL": f"http://127.0.0.1:{servico_inexistente}",
                "HTTP_TIMEOUT_SECONDS": "1"})
    p = subprocess.Popen([sys.executable, "-m", "servico_vendas.app"],
                         cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        for _ in range(100):
            try:
                if requests.get(f"http://127.0.0.1:{porta}/health", timeout=.2).ok:
                    break
            except requests.RequestException:
                pass
            time.sleep(.1)
        resp = post(f"http://127.0.0.1:{porta}/pedidos",
                    {"sessaoId": 1, "ingressos": [{"tipo": "INTEIRA"}]})
        assert resp.status_code == 503
        assert "indisponível" in resp.json()["mensagem"].lower()
    finally:
        p.terminate()
        p.wait(timeout=5)
