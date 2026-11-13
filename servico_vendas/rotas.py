from flask import Blueprint, jsonify
from comum.api import json_objeto
from . import regras

bp = Blueprint("vendas", __name__)

@bp.post("/pedidos")
def criar():
    return jsonify(regras.criar_pedido(json_objeto())), 201

@bp.get("/pedidos")
def listar():
    return jsonify(regras.listar_pedidos())

@bp.get("/pedidos/<int:id>")
def buscar(id):
    return jsonify(regras.buscar_pedido(id).para_json())

@bp.get("/ingressos")
def listar_ingressos():
    return jsonify(regras.listar_ingressos())

@bp.get("/ingressos/<int:id>")
def buscar_ingresso(id):
    return jsonify(regras.buscar_ingresso(id).para_json())

@bp.post("/pedidos/<int:id>/compensar")
def compensar(id):
    return jsonify(regras.compensar(id))
