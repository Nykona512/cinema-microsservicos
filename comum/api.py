"""Validação básica e respostas de erro no formato usado pela API Java."""
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from flask import jsonify, request
from werkzeug.exceptions import HTTPException


class ErroAPI(Exception):
    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


class ErroIntegracao(ErroAPI):
    def __init__(self, mensagem, status=503, incerto=False):
        super().__init__(mensagem, status)
        self.incerto = incerto


def agora_local():
    """Horário do cinema, independente do fuso da hospedagem."""
    zona = os.getenv("CINEMA_TIMEZONE", "America/Sao_Paulo")
    return datetime.now(ZoneInfo(zona)).replace(tzinfo=None)


def configurar_erros(app):
    @app.errorhandler(ErroAPI)
    def erro_api(erro):
        return jsonify({
            "status": erro.status,
            "erro": {400: "Bad Request", 404: "Not Found", 409: "Conflict",
                     503: "Service Unavailable"}.get(erro.status, "Error"),
            "mensagem": erro.mensagem,
            "caminho": request.path,
            "timestamp": agora_local().isoformat(timespec="seconds"),
            "campos": []
        }), erro.status

    @app.errorhandler(HTTPException)
    def erro_http(erro):
        return erro_api(ErroAPI(erro.description, erro.code or 500))


def json_objeto():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ErroAPI("Envie um objeto JSON válido.")
    return payload


def texto_nao_vazio(dados, chave):
    valor = dados.get(chave)
    if not isinstance(valor, str) or not valor.strip():
        raise ErroAPI(f"O campo '{chave}' deve ser um texto não vazio.")
    return valor.strip()


def inteiro_positivo(dados, chave):
    valor = dados.get(chave)
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < 1:
        raise ErroAPI(f"O campo '{chave}' deve ser um inteiro maior que zero.")
    return valor


def valor_monetario(dados, chave):
    valor = dados.get(chave)
    if isinstance(valor, bool) or not isinstance(valor, (str, float, int, Decimal)):
        raise ErroAPI(f"O campo '{chave}' deve ser monetário e maior que zero.")
    try:
        montante = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        raise ErroAPI(f"Valor monetário inválido em '{chave}'.")
    if not montante.is_finite() or montante < Decimal("0.01"):
        raise ErroAPI(f"O campo '{chave}' deve ser maior ou igual a 0.01.")
    if montante.as_tuple().exponent < -2:
        raise ErroAPI(f"O campo '{chave}' aceita no máximo duas casas decimais.")
    return montante.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def inicio_local(dados, chave="inicio"):
    valor = dados.get(chave)
    if not isinstance(valor, str):
        raise ErroAPI(f"'{chave}' deve ser data ISO, exemplo 2026-12-10T14:00:00.")
    try:
        dt = datetime.fromisoformat(valor)
    except ValueError:
        raise ErroAPI(f"'{chave}' deve ser data ISO, exemplo 2026-12-10T14:00:00.")
    if dt.tzinfo is not None:
        raise ErroAPI(f"'{chave}' não deve conter fuso horário (horário local do cinema).")
    return dt


def reais(valor):
    return float(Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
