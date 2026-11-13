from flask_sqlalchemy import SQLAlchemy
from comum.api import reais, agora_local

db = SQLAlchemy()


class Pedido(db.Model):
    __tablename__ = "pedido"
    id = db.Column(db.Integer, primary_key=True)
    data_hora = db.Column(db.DateTime, nullable=False, default=agora_local)
    sessao_id = db.Column(db.Integer, nullable=False)  # ID remoto, SEM ForeignKey
    valor_total = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    status = db.Column(db.String(28), nullable=False, default="PENDENTE")
    reserva_id = db.Column(db.String(36), nullable=False, unique=True)
    mensagem_falha = db.Column(db.String(500), nullable=True)
    ingressos = db.relationship("Ingresso", back_populates="pedido", cascade="all, delete-orphan")

    def para_json(self):
        return {"id": self.id, "valorTotal": reais(self.valor_total),
                "status": self.status,
                "ingressos": [i.para_json() for i in sorted(self.ingressos, key=lambda x: x.id)]}


class Ingresso(db.Model):
    __tablename__ = "ingresso"
    id = db.Column(db.Integer, primary_key=True)
    sessao_id = db.Column(db.Integer, nullable=False)  # ID remoto, SEM ForeignKey
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    pedido = db.relationship("Pedido", back_populates="ingressos")

    def para_json(self):
        return {"id": self.id, "sessaoId": self.sessao_id,
                "pedidoId": self.pedido_id, "tipo": self.tipo,
                "valor": reais(self.valor)}
