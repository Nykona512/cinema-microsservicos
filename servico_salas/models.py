from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Sala(db.Model):
    __tablename__ = "sala"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    capacidade = db.Column(db.Integer, nullable=False)

    def para_json(self):
        return {"id": self.id, "nome": self.nome, "capacidade": self.capacidade}
