import os
from comum.cliente_http import chamar

def buscar_sala(sala_id):
    base = os.getenv("SALAS_URL", "http://127.0.0.1:5002").rstrip("/")
    return chamar("GET", f"{base}/salas/{sala_id}")
