from comum.api import ErroAPI, inteiro_positivo, texto_nao_vazio
from .models import Sala, db


def listar():
    return [s.para_json() for s in Sala.query.order_by(Sala.id).all()]


def buscar(id):
    sala = db.session.get(Sala, id)
    if sala is None:
        raise ErroAPI(f"Sala não encontrada: {id}", 404)
    return sala


def criar(dados):
    sala = Sala(nome=texto_nao_vazio(dados, "nome"),
                capacidade=inteiro_positivo(dados, "capacidade"))
    db.session.add(sala)
    db.session.commit()
    return sala.para_json()


def atualizar(id, dados):
    sala = buscar(id)
    sala.nome = texto_nao_vazio(dados, "nome")
    sala.capacidade = inteiro_positivo(dados, "capacidade")
    db.session.commit()
    return sala.para_json()


def excluir(id):
    db.session.delete(buscar(id))
    db.session.commit()
