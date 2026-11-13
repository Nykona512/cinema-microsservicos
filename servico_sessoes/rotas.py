from flask import Blueprint, jsonify
from comum.api import json_objeto
from . import regras

bp = Blueprint("sessoes", __name__)

@bp.get("/sessoes")
def listar():
    return jsonify(regras.listar())

@bp.get("/sessoes/<int:id>")
def buscar(id):
    return jsonify(regras.buscar(id).para_json())

@bp.post("/sessoes")
def criar():
    return jsonify(regras.criar(json_objeto())), 201

@bp.put("/sessoes/<int:id>")
def atualizar(id):
    return jsonify(regras.atualizar(id, json_objeto()))

@bp.delete("/sessoes/<int:id>")
def excluir(id):
    regras.excluir(id)
    return "", 204

@bp.post("/sessoes/<int:id>/reservas")
def reservar(id):
    return jsonify(regras.reservar(id, json_objeto())), 201

@bp.post("/sessoes/<int:id>/reservas/<reserva_id>/cancelar")
def cancelar_reserva(id, reserva_id):
    return jsonify(regras.cancelar_reserva(id, reserva_id))
