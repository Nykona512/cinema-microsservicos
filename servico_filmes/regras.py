from comum.api import ErroAPI, inteiro_positivo, texto_nao_vazio
from .models import Filme, db


def listar():
    return [f.para_json() for f in Filme.query.order_by(Filme.id).all()]


def buscar(id):
    filme = db.session.get(Filme, id)
    if filme is None:
        raise ErroAPI(f"Filme não encontrado: {id}", 404)
    return filme


def criar(dados):
    filme = Filme(titulo=texto_nao_vazio(dados, "titulo"),
                  duracao_minutos=inteiro_positivo(dados, "duracaoMinutos"))
    db.session.add(filme)
    db.session.commit()
    return filme.para_json()


def atualizar(id, dados):
    filme = buscar(id)
    filme.titulo = texto_nao_vazio(dados, "titulo")
    filme.duracao_minutos = inteiro_positivo(dados, "duracaoMinutos")
    db.session.commit()
    return filme.para_json()


def excluir(id):
    db.session.delete(buscar(id))
    db.session.commit()
