from flask import Blueprint, jsonify
from comum.api import json_objeto
from . import regras

bp = Blueprint("salas", __name__)

@bp.get("/salas")
def listar():
    return jsonify(regras.listar())

@bp.get("/salas/<int:id>")
def buscar(id):
    return jsonify(regras.buscar(id).para_json())

@bp.post("/salas")
def criar():
    return jsonify(regras.criar(json_objeto())), 201

@bp.put("/salas/<int:id>")
def atualizar(id):
    return jsonify(regras.atualizar(id, json_objeto()))

@bp.delete("/salas/<int:id>")
def excluir(id):
    regras.excluir(id)
    return "", 204
