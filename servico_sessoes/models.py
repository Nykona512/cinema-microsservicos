from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Sessao(db.Model):
    __tablename__ = "sessao"
    id = db.Column(db.Integer, primary_key=True)
    filme_id = db.Column(db.Integer, nullable=False)  # ID remoto, NÃO ForeignKey
    sala_id = db.Column(db.Integer, nullable=False)   # ID remoto, NÃO ForeignKey
    inicio = db.Column(db.DateTime, nullable=False)
    fim_ocupacao = db.Column(db.DateTime, nullable=False)
    preco_inteira = db.Column(db.Numeric(10, 2), nullable=False)
    capacidade = db.Column(db.Integer, nullable=False)  # snapshot na criação
    ocupados = db.Column(db.Integer, nullable=False, default=0)
    meias = db.Column(db.Integer, nullable=False, default=0)

    def para_json(self):
        from comum.api import reais
        return {"id": self.id, "filmeId": self.filme_id, "salaId": self.sala_id,
                "inicio": self.inicio.isoformat(timespec="seconds"),
                "precoInteira": reais(self.preco_inteira),
                "capacidade": self.capacidade,
                "vagasDisponiveis": self.capacidade - self.ocupados,
                "meiasDisponiveis": (self.capacidade * 40 // 100) - self.meias}


class Reserva(db.Model):
    __tablename__ = "reserva"
    id = db.Column(db.String(36), primary_key=True)  # UUID enviado por Vendas
    sessao_id = db.Column(db.Integer, db.ForeignKey("sessao.id"), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    meias = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(16), nullable=False, default="ATIVA")
