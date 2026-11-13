from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Filme(db.Model):
    __tablename__ = "filme"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(180), nullable=False)
    duracao_minutos = db.Column(db.Integer, nullable=False)

    def para_json(self):
        return {"id": self.id, "titulo": self.titulo, "duracaoMinutos": self.duracao_minutos}
