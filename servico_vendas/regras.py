"""R3, preço do ingresso e compra compensável entre dois bancos independentes."""
import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
from sqlalchemy.exc import SQLAlchemyError
from comum.api import ErroAPI, ErroIntegracao, agora_local, inteiro_positivo
from .models import db, Pedido, Ingresso
from .sessoes_helper import buscar_sessao, reservar, cancelar

log = logging.getLogger(__name__)


def buscar_pedido(id):
    pedido = db.session.get(Pedido, id)
    if pedido is None:
        raise ErroAPI(f"Pedido não encontrado: {id}", 404)
    return pedido


def validar_ingressos(dados):
    sessao_id = inteiro_positivo(dados, "sessaoId")
    itens = dados.get("ingressos")
    if not isinstance(itens, list) or not itens:
        raise ErroAPI("O pedido deve conter ao menos um ingresso.")
    if len(itens) > 6:
        raise ErroAPI("R3: O limite máximo permitido é de 6 ingressos por pedido.")
    tipos = []
    for item in itens:
        if not isinstance(item, dict) or item.get("tipo") not in ("INTEIRA", "MEIA"):
            raise ErroAPI("Cada ingresso deve conter 'tipo': 'INTEIRA' ou 'MEIA'.")
        tipos.append(item["tipo"])
    return sessao_id, tipos


def _registrar_falha(pedido, mensagem, tentar_compensar):
    """Compensa reserva remota; nunca confirma pedido se estado for incerto."""
    db.session.rollback()
    compensou = not tentar_compensar
    if tentar_compensar:
        try:
            cancelar(pedido.sessao_id, pedido.reserva_id)
            compensou = True
        except ErroIntegracao as erro:
            # 404 significa reserva não encontrada, logo não há vagas presas.
            if erro.status == 404:
                compensou = True
            else:
                log.error("Compensação pendente no pedido %s: %s", pedido.id, erro)
    salvo = db.session.get(Pedido, pedido.id)
    if salvo is not None:
        salvo.status = "CANCELADO" if compensou else "COMPENSACAO_PENDENTE"
        salvo.mensagem_falha = mensagem[:500]
        db.session.commit()
    return compensou


def criar_pedido(dados):
    sessao_id, tipos = validar_ingressos(dados)
    sessao = buscar_sessao(sessao_id)  # integração GET adicional
    inicio = datetime.fromisoformat(sessao["inicio"])
    if inicio <= agora_local():
        raise ErroAPI("A sessão já começou.")
    preco = Decimal(str(sessao["precoInteira"]))
    pedido = Pedido(sessao_id=sessao_id, valor_total=Decimal("0.00"),
                    status="PENDENTE", reserva_id=str(uuid4()))
    db.session.add(pedido)
    db.session.commit()  # primeiro grava pendência rastreável
    try:
        reservar(sessao_id, pedido.reserva_id, len(tipos), tipos.count("MEIA"))
    except ErroIntegracao as erro:
        # Timeout depois de POST pode significar reserva efetivada; compensa por UUID.
        compensou = _registrar_falha(pedido, erro.mensagem, tentar_compensar=erro.incerto)
        if not compensou:
            raise ErroAPI("Compra não concluída; compensação pendente. Consulte o pedido.", 503)
        raise ErroAPI(erro.mensagem, erro.status)
    try:
        total = Decimal("0.00")
        for tipo in tipos:
            valor = (preco / 2 if tipo == "MEIA" else preco).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP)
            total += valor
            db.session.add(Ingresso(sessao_id=sessao_id, pedido_id=pedido.id,
                                    tipo=tipo, valor=valor))
        pedido.valor_total = total
        pedido.status = "CONFIRMADO"
        db.session.commit()
        return pedido.para_json()
    except SQLAlchemyError as erro:
        log.exception("Falha ao gravar pedido %s", pedido.id)
        compensou = _registrar_falha(pedido, str(erro), tentar_compensar=True)
        if not compensou:
            raise ErroAPI("Compra não concluída; compensação pendente. Consulte o pedido.", 503)
        raise ErroAPI("Compra não concluída: falha ao salvar pedido; reserva desfeita.", 503)


def listar_pedidos():
    return [p.para_json() for p in Pedido.query.order_by(Pedido.id).all()]


def listar_ingressos():
    return [i.para_json() for i in Ingresso.query.order_by(Ingresso.id).all()]


def buscar_ingresso(id):
    ingresso = db.session.get(Ingresso, id)
    if ingresso is None:
        raise ErroAPI(f"Ingresso não encontrado: {id}", 404)
    return ingresso


def compensar(id):
    pedido = buscar_pedido(id)
    if pedido.status != "COMPENSACAO_PENDENTE":
        raise ErroAPI("Somente pedidos com COMPENSACAO_PENDENTE podem ser compensados.", 409)
    try:
        cancelar(pedido.sessao_id, pedido.reserva_id)
    except ErroIntegracao as erro:
        if erro.status != 404:
            raise
    pedido.status = "CANCELADO"
    pedido.mensagem_falha = None
    db.session.commit()
    return pedido.para_json()
