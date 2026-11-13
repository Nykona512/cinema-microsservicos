import os
from pathlib import Path
from flask import Flask, jsonify
from comum.api import configurar_erros
from .models import db


def create_app():
    app = Flask(__name__)
    app.json.ensure_ascii = False
    caminho = Path(__file__).resolve().parent / "dados" / "sessoes.db"
    caminho.parent.mkdir(exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", f"sqlite:///{caminho}")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    from .rotas import bp
    app.register_blueprint(bp)
    configurar_erros(app)
    @app.get("/health")
    def health():
        return jsonify({"servico": "sessoes", "status": "ok"})
    with app.app_context():
        db.create_all()
    return app

app = create_app()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5003")), debug=False)
