"""Validação R2 e reserva atômica R1/lotação do microsserviço Sessões."""
from datetime import timedelta
from uuid import UUID
from sqlalchemy import cast, Integer, update
from sqlalchemy.exc import IntegrityError
from comum.api import ErroAPI, agora_local, inteiro_positivo, inicio_local, valor_monetario
from .models import db, Sessao, Reserva
from .filmes_helper import buscar_filme
from .salas_helper import buscar_sala


def listar():
    return [s.para_json() for s in Sessao.query.order_by(Sessao.id).all()]


def buscar(id):
    sessao = db.session.get(Sessao, id)
    if sessao is None:
        raise ErroAPI(f"Sessão não encontrada: {id}", 404)
    return sessao


def conferir_conflito(sala_id, novo_inicio, novo_fim, ignorar_id=None):
    consulta = Sessao.query.filter_by(sala_id=sala_id)
    if ignorar_id is not None:
        consulta = consulta.filter(Sessao.id != ignorar_id)
    for sessao in consulta.all():
        if novo_inicio < sessao.fim_ocupacao and sessao.inicio < novo_fim:
            raise ErroAPI("R2: O horário informado apresenta conflito com outra sessão nesta sala.")


def validar_sessao(dados, ignorar_id=None):
    filme_id = inteiro_positivo(dados, "filmeId")
    sala_id = inteiro_positivo(dados, "salaId")
    inicio = inicio_local(dados)
    preco = valor_monetario(dados, "precoInteira")
    # DUAS integrações GET entre serviços, exigidas pelo trabalho.
    filme = buscar_filme(filme_id)
    sala = buscar_sala(sala_id)
    fim = inicio + timedelta(minutes=int(filme["duracaoMinutos"]) + 20)
    capacidade = int(sala["capacidade"])
    conferir_conflito(sala_id, inicio, fim, ignorar_id)
    return filme_id, sala_id, inicio, fim, preco, capacidade


def criar(dados):
    filme_id, sala_id, inicio, fim, preco, capacidade = validar_sessao(dados)
    sessao = Sessao(filme_id=filme_id, sala_id=sala_id, inicio=inicio,
                    fim_ocupacao=fim, preco_inteira=preco, capacidade=capacidade,
                    ocupados=0, meias=0)
    db.session.add(sessao)
    db.session.commit()
    return sessao.para_json()


def atualizar(id, dados):
    sessao = buscar(id)
    if sessao.ocupados:
        raise ErroAPI("Sessão com ingressos vendidos não pode ser alterada.", 409)
    filme_id, sala_id, inicio, fim, preco, capacidade = validar_sessao(dados, id)
    sessao.filme_id, sessao.sala_id = filme_id, sala_id
    sessao.inicio, sessao.fim_ocupacao = inicio, fim
    sessao.preco_inteira, sessao.capacidade = preco, capacidade
    db.session.commit()
    return sessao.para_json()


def excluir(id):
    sessao = buscar(id)
    if sessao.ocupados or Reserva.query.filter_by(sessao_id=id).first() is not None:
        raise ErroAPI("Sessão com histórico de reservas não pode ser excluída.", 409)
    db.session.delete(sessao)
    db.session.commit()


def validar_uuid(valor):
    try:
        return str(UUID(valor))
    except (ValueError, TypeError, AttributeError):
        raise ErroAPI("reservaId deve ser um UUID válido.")


def reservar(id, dados):
    reserva_id = validar_uuid(dados.get("reservaId"))
    quantidade = inteiro_positivo(dados, "quantidade")
    meias = dados.get("meias")
    if isinstance(meias, bool) or not isinstance(meias, int) or meias < 0 or meias > quantidade:
        raise ErroAPI("meias deve ser um inteiro entre zero e quantidade.")
    sessao = buscar(id)
    existente = db.session.get(Reserva, reserva_id)
    if existente:
        if (existente.sessao_id == id and existente.quantidade == quantidade and
                existente.meias == meias and existente.status == "ATIVA"):
            return {"reservaId": reserva_id, "status": "ATIVA", "repetida": True}
        raise ErroAPI("reservaId já utilizado com outros dados ou cancelado.", 409)
    if sessao.inicio <= agora_local():
        raise ErroAPI("A sessão já começou.")
    # UPDATE condicionado: evita overbooking mesmo entre duas requisições concorrentes.
    comando = (update(Sessao)
               .where(Sessao.id == id)
               .where(Sessao.ocupados + quantidade <= Sessao.capacidade)
               .where(Sessao.meias + meias <= cast(Sessao.capacidade * 0.40, Integer))
               .values(ocupados=Sessao.ocupados + quantidade,
                       meias=Sessao.meias + meias))
    atualizados = db.session.execute(comando).rowcount
    if atualizados != 1:
        db.session.rollback()
        estado = buscar(id)
        if estado.ocupados + quantidade > estado.capacidade:
            raise ErroAPI("Não há mais ingressos disponíveis para esta sessão.")
        raise ErroAPI("R1: A cota de meia-entrada desta sessão (40%) já foi atingida.")
    db.session.add(Reserva(id=reserva_id, sessao_id=id, quantidade=quantidade,
                           meias=meias, status="ATIVA"))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ErroAPI("Reserva concorrente duplicada; consulte a reserva anterior.", 409)
    return {"reservaId": reserva_id, "status": "ATIVA", "repetida": False}


def cancelar_reserva(id, reserva_id):
    reserva_id = validar_uuid(reserva_id)
    buscar(id)
    reserva = db.session.get(Reserva, reserva_id)
    if reserva is None:
        # Tombstone: se a solicitação de reserva chegar DEPOIS de um timeout,
        # o UUID cancelado impede que vagas sejam ocupadas tardiamente.
        db.session.add(Reserva(id=reserva_id, sessao_id=id,
                               quantidade=0, meias=0, status="CANCELADA"))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return cancelar_reserva(id, reserva_id)
        return {"reservaId": reserva_id, "status": "CANCELADA", "semReserva": True}
    if reserva.sessao_id != id:
        raise ErroAPI("Esta reserva pertence a outra sessão.", 409)
    if reserva.status == "CANCELADA":
        return {"reservaId": reserva_id, "status": "CANCELADA", "repetida": True}
    # SQLite serializa escritores; transação cancela apenas uma vez a reserva.
    ok = db.session.execute(
        update(Reserva).where(Reserva.id == reserva_id, Reserva.status == "ATIVA")
        .values(status="CANCELADA")
    ).rowcount
    if ok:
        db.session.execute(
            update(Sessao).where(Sessao.id == id)
            .values(ocupados=Sessao.ocupados - reserva.quantidade,
                    meias=Sessao.meias - reserva.meias)
        )
    db.session.commit()
    return {"reservaId": reserva_id, "status": "CANCELADA", "repetida": not bool(ok)}
