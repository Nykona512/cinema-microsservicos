import os
from comum.cliente_http import chamar

def buscar_filme(filme_id):
    base = os.getenv("FILMES_URL", "http://127.0.0.1:5001").rstrip("/")
    return chamar("GET", f"{base}/filmes/{filme_id}")
