"""Verifica exigências estruturais sem depender da instalação do Flask."""
import ast
from pathlib import Path

raiz = Path(__file__).resolve().parents[1]
servicos = {
    "filmes": ("5001", "filmes.db"),
    "salas": ("5002", "salas.db"),
    "sessoes": ("5003", "sessoes.db"),
    "vendas": ("5004", "vendas.db"),
}
for nome, (porta, banco) in servicos.items():
    pasta = raiz / f"servico_{nome}"
    for arquivo in ("app.py", "models.py", "regras.py", "rotas.py"):
        codigo = (pasta / arquivo).read_text(encoding="utf-8")
        ast.parse(codigo, filename=f"{nome}/{arquivo}")
    codigo_app = (pasta / "app.py").read_text(encoding="utf-8")
    assert porta in codigo_app, f"Porta de {nome} incorreta"
    assert banco in codigo_app, f"Banco de {nome} incorreto"
    print(f"OK {nome:<8} Flask / separação de arquivos / SQLite {banco} / porta {porta}")

arquivo_filmes = (raiz / "servico_sessoes" / "filmes_helper.py").read_text()
arquivo_salas = (raiz / "servico_sessoes" / "salas_helper.py").read_text()
arquivo_sessoes = (raiz / "servico_vendas" / "sessoes_helper.py").read_text()
assert '"GET"' in arquivo_filmes
assert '"GET"' in arquivo_salas
assert '"POST"' in arquivo_sessoes
for arquivo in ("README.md", "requirements.txt", "rest-client/integracoes.http"):
    assert (raiz / arquivo).exists()

for arquivo in raiz.rglob("*.py"):
    ast.parse(arquivo.read_text(encoding="utf8"), filename=str(arquivo))
print("OK 2 integrações GET + 1 integração POST")
print("OK sintaxe Python de todos os arquivos")
print("NOTA: isto não substitui execução real dos microsserviços e testes HTTP.")
