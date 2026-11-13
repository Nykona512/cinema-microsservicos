from flask import Blueprint, jsonify
from comum.api import json_objeto
from . import regras

bp = Blueprint("filmes", __name__)

@bp.get("/filmes")
def listar():
    return jsonify(regras.listar())

@bp.get("/filmes/<int:id>")
def buscar(id):
    return jsonify(regras.buscar(id).para_json())

@bp.post("/filmes")
def criar():
    return jsonify(regras.criar(json_objeto())), 201

@bp.put("/filmes/<int:id>")
def atualizar(id):
    return jsonify(regras.atualizar(id, json_objeto()))

@bp.delete("/filmes/<int:id>")
def excluir(id):
    regras.excluir(id)
    return "", 204
