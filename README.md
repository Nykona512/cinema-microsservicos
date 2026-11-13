# Sistema de Ingressos de Cinema — Python e microsserviços

Adaptação do projeto Java/Spring Boot `projeto-entretenimento-cultura` para a avaliação de **Sistemas Distribuídos (SATC)**. O projeto utiliza **Python, Flask, Flask-SQLAlchemy, SQLite, JSON e requests**, com quatro APIs e bancos separados.

## 1. Documento de requisitos

### Propósito

Permitir que um cinema cadastre filmes, salas e sessões e registre compras de ingressos, evitando conflitos de horários, superlotação, venda excessiva de meia-entrada e compras acima do limite. Esta é uma API acadêmica; não processa pagamentos reais.

### Usuários

- **Administrador/atendente do cinema:** gerencia filmes, salas e sessões, acompanha pedidos e ingressos.
- **Cliente:** consulta programação e solicita compra de ingressos.

### Requisitos funcionais

| ID | Requisito |
|---|---|
| RF01 | Cadastrar, consultar, atualizar e remover filmes (título, duração). |
| RF02 | Cadastrar, consultar, atualizar e remover salas (nome, capacidade). |
| RF03 | Cadastrar e consultar sessões com filme, sala, início e preço da inteira. |
| RF04 | Impedir sessões sobrepostas na mesma sala, contabilizando 20 min de limpeza (**R2**). |
| RF05 | Registrar compras com até seis ingressos por pedido (**R3**). |
| RF06 | Aceitar inteira e meia; limitar meias a 40% da capacidade e cobrar metade do preço (**R1**). |
| RF07 | Não vender ingressos de sessão iniciada ou acima da lotação. |
| RF08 | Consultar pedidos e ingressos emitidos. |
| RF09 | Registrar a reserva de vagas em outro serviço por HTTP, com compensação se a compra falhar. |
| RF10 | Responder JSON com erros claros quando houver dados inválidos ou serviço indisponível. |

**Fora do escopo:** autenticação, pagamento, numeração de poltronas e verificação de documentos de meia-entrada.

## 2. Descritivo técnico e divisão da equipe

| Microsserviço | Diretório | Porta local | SQLite | Função |
|---|---|---:|---|---|
| Filmes | `servico_filmes/` | 5001 | `servico_filmes/dados/filmes.db` | CRUD de filmes. |
| Salas | `servico_salas/` | 5002 | `servico_salas/dados/salas.db` | CRUD de salas. |
| Sessões | `servico_sessoes/` | 5003 | `servico_sessoes/dados/sessoes.db` | Programação, regra de horários, disponibilidade, reservas e cancelamento compensatório. |
| Vendas | `servico_vendas/` | 5004 | `servico_vendas/dados/vendas.db` | Pedidos, ingressos, preços e coordenação da compra. |

> **Atribuição:** a equipe deve preencher com os quatro responsáveis antes da entrega. Sugestão: um integrante por serviço.

Cada serviço tem `app.py` (inicialização), `models.py` (tabelas), `regras.py` (negócio), `rotas.py` (API) e, quando necessário, `<outro_servico>_helper.py` (requisições HTTP com timeout). A pasta `comum/` contém apenas validação e tratamento HTTP reutilizáveis; ela **não** faz acesso a banco compartilhado.

### Integrações exigidas pela avaliação

| # | Origem → Destino | Método | Objetivo |
|---|---|---|---|
| 1 | Sessões → Filmes | `GET /filmes/{id}` | Obter a duração do filme para aplicar R2. |
| 2 | Sessões → Salas | `GET /salas/{id}` | Validar existência da sala e obter sua capacidade. |
| 3 | Vendas → Sessões | `POST /sessoes/{id}/reservas` | Atualizar quantidade ocupada e meia-entrada em outro serviço. |
| Extra | Vendas → Sessões | `GET /sessoes/{id}` | Verificar sessão e preço antes da compra. |
| Compensação | Vendas → Sessões | `POST /sessoes/{id}/reservas/{uuid}/cancelar` | Desfazer reserva caso a operação de venda falhe. |

**Regra arquitetural:** `filmeId` e `salaId` em Sessões, e `sessaoId` em Vendas, são **IDs simples**; não há ForeignKey entre os bancos nem acesso direto a banco de outro serviço. Vendas pode usar FK entre `pedido` e `ingresso` porque ambas as tabelas pertencem ao mesmo serviço.

### Preservação das regras originais de Java

- **R1:** máximo de `floor(capacidade × 0,40)` meias por sessão; meia custa `precoInteira × 0,50`, com arredondamento decimal HALF_UP.
- **R2:** para criar sessão, a janela ocupada é `[inicio, inicio + duração do filme + 20 minutos)`; duas janelas não podem se sobrepor na mesma sala.
- **R3:** entre 1 e 6 ingressos em cada pedido.
- **Lotação:** reservas atualizam ocupação de forma condicional/atômica dentro do SQLite de Sessões, evitando overbooking.

As datas são horários locais do cinema; o padrão é `America/Sao_Paulo` (configurável pela variável `CINEMA_TIMEZONE`). A capacidade e o fim da ocupação são **fotografados na criação** da sessão. Alterar posteriormente a duração de um filme ou a capacidade de uma sala não modifica sessões antigas. Essa é uma decisão de adaptação para manter independência entre microsserviços; o Java original utiliza entidades relacionadas diretamente.

### Consistência e tratamento de falhas

1. Vendas valida o pedido e consulta a sessão.
2. Vendas grava um `Pedido` com status `PENDENTE` e um UUID de reserva.
3. Vendas envia `POST` ao serviço Sessões para reservar a quantidade.
4. Quando a reserva é confirmada, Vendas grava ingressos e muda o pedido para `CONFIRMADO`.
5. Se a gravação falha ou há timeout incerto, Vendas solicita compensação por `POST .../cancelar`; a mesma reserva não é cancelada duas vezes.
6. Se a compensação não puder ser confirmada, o pedido fica `COMPENSACAO_PENDENTE` e pode ser reprocessado pela rota `POST /pedidos/{id}/compensar`.

Sessões registra um **UUID cancelado** mesmo quando a reserva ainda não existe (tombstone), bloqueando uma reserva tardia com o mesmo UUID após um timeout. Essa abordagem melhora a recuperação de falhas, mas **não é uma transação distribuída totalmente atômica**; para produção recomenda-se autenticação, outbox/eventos, reconciliação periódica e banco persistente.

## 3. Como executar no VS Code

**Pré-requisitos:** Python 3.10+ (recomendado 3.12), VS Code e acesso à internet para instalar pacotes uma vez.

Abra a pasta do projeto no VS Code. No PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Se a ativação pelo PowerShell for bloqueada, rode `\.venv\Scripts\python.exe -m pip install -r requirements.txt` e use esse executável nos comandos abaixo.

**Abra quatro terminais, todos na raiz do repositório**, e execute:

```powershell
# Terminal 1
python -m servico_filmes.app

# Terminal 2
python -m servico_salas.app

# Terminal 3
python -m servico_sessoes.app

# Terminal 4
python -m servico_vendas.app
```

No Linux/macOS, ative o ambiente com `source .venv/bin/activate`. Não rode `python app.py` dentro da pasta do serviço: a execução correta é `python -m servico_*.app` **na raiz**, para resolver as importações.

Verifique no navegador:

- http://127.0.0.1:5001/health
- http://127.0.0.1:5002/health
- http://127.0.0.1:5003/health
- http://127.0.0.1:5004/health

Os arquivos SQLite são criados automaticamente na primeira execução. Para apagar dados de testes, encerre os servidores e remova os quatro arquivos `.db` (cuidado: você perderá os cadastros).

## 4. Demonstração completa no REST Client (VS Code)

Instale a extensão **REST Client** (autor: Huachao Mao, ID `humao.rest-client`) no VS Code. Com os quatro serviços iniciados, abra os arquivos da pasta `rest-client/` e clique em **Send Request** acima da requisição desejada. Cada requisição `.http` traz a URL, o método e, quando necessário, o corpo JSON. Não há importação de coleção.

- `rest-client/filmes.http`: cadastro e consultas de filmes.
- `rest-client/salas.http`: cadastro e consultas de salas.
- `rest-client/sessoes.http`: cadastro e consultas de sessões.
- `rest-client/vendas.http`: compras, pedidos e ingressos.
- `rest-client/integracoes.http`: consultas GET entre serviços, compra que dispara POST e testes de falha.

**Ordem sugerida:** cadastrar filme → cadastrar sala → criar sessão → consultar vagas → fazer compra → consultar vagas novamente. Os IDs `1` nos arquivos partem de bancos vazios. Se necessário, altere os IDs. Para testar em URLs públicas no Render, modifique as variáveis no começo de cada arquivo `.http`.

Abaixo estão os mesmos exemplos com os dados de demonstração.

**Etapa 1 — Cadastrar filme**, `POST http://127.0.0.1:5001/filmes`:

```json
{"titulo":"Interestelar","duracaoMinutos":169}
```

**Etapa 2 — Cadastrar sala**, `POST http://127.0.0.1:5002/salas`:

```json
{"nome":"Sala 1","capacidade":20}
```

**Etapa 3 — Cadastrar sessão**, `POST http://127.0.0.1:5003/sessoes`:

```json
{"filmeId":1,"salaId":1,"inicio":"2026-12-10T14:00:00","precoInteira":30.00}
```

Aqui aparecem os dois **GET entre microsserviços** (Sessões → Filmes e Sessões → Salas). Acesse os logs dos três terminais para demonstrá-los.

**Etapa 4 — Fazer compra**, `POST http://127.0.0.1:5004/pedidos`:

```json
{"sessaoId":1,"ingressos":[{"tipo":"INTEIRA"},{"tipo":"MEIA"}]}
```

O resultado terá `valorTotal: 45.0`, dois ingressos e `status: "CONFIRMADO"`. Aqui Vendas faz **GET + POST** em Sessões, que passa a registrar duas vagas ocupadas.

**Etapa 5 — Conferir alteração remota**, `GET http://127.0.0.1:5003/sessoes/1`:

```json
{"id":1,"filmeId":1,"salaId":1,"inicio":"2026-12-10T14:00:00","precoInteira":30.0,"capacidade":20,"vagasDisponiveis":18,"meiasDisponiveis":7}
```

A resposta possui os campos antigos da API Java e acrescenta indicadores de disponibilidade. Os IDs `1` pressupõem banco inicial vazio; caso não estejam vazios, use os IDs devolvidos pelos POST.

Para gerar os registros de exemplo automaticamente, use `python scripts/popular_demo.py` com os quatro serviços já ativos.

## 5. Rotas REST

| Serviço | Método | Rota | Finalidade |
|---|---|---|---|
| Filmes | GET / POST | `/filmes` | Listar / criar filme |
| Filmes | GET / PUT / DELETE | `/filmes/{id}` | Buscar / atualizar / excluir |
| Salas | GET / POST | `/salas` | Listar / criar sala |
| Salas | GET / PUT / DELETE | `/salas/{id}` | Buscar / atualizar / excluir |
| Sessões | GET / POST | `/sessoes` | Listar / criar sessão |
| Sessões | GET / PUT / DELETE | `/sessoes/{id}` | Buscar / atualizar / excluir, se permitido |
| Sessões | POST | `/sessoes/{id}/reservas` | Criar reserva idempotente |
| Sessões | POST | `/sessoes/{id}/reservas/{uuid}/cancelar` | Desfazer reserva |
| Vendas | POST / GET | `/pedidos` | Comprar / listar pedidos |
| Vendas | GET | `/pedidos/{id}` | Consultar pedido |
| Vendas | GET | `/ingressos` | Listar ingressos |
| Vendas | GET | `/ingressos/{id}` | Consultar ingresso |
| Vendas | POST | `/pedidos/{id}/compensar` | Tentar compensação pendente |
| Todos | GET | `/health` | Teste de saúde |

**Observação:** a API de Vendas trata pedidos como registros de compra/auditoria. Não oferece PUT/DELETE de pedidos confirmados; altera apenas seu status no fluxo de compensação, evitando apagar o histórico. A exclusão de filmes ou salas referenciados por sessões antigas não é bloqueada automaticamente entre serviços; não remova esses cadastros em uma demonstração com sessões existentes.

### Padrão de erros

A estrutura JSON mantém as chaves do projeto Java: `status`, `erro`, `mensagem`, `caminho`, `timestamp`, `campos`. Regras inválidas retornam `400`, não encontrado `404`, conflitos de estado `409` e falha de integração `503`. A mensagem é descritiva e a aplicação continua respondendo quando outro serviço está indisponível.

## 6. Testes

Com as dependências instaladas, execute na **raiz**:

```powershell
python -m pytest -v tests/
```

Os testes iniciam instâncias isoladas dos quatro serviços em portas livres e com quatro bancos SQLite temporários. Verificam compra normal, cota de meia-entrada, limite R3, conflito R2, integridade entre serviços e idempotência da reserva.

## 7. Publicação no Render

Crie **quatro Web Services** apontando para o mesmo repositório GitHub, com o diretório raiz do repo e o comando de build `pip install -r requirements.txt`.

| Web Service | Start command |
|---|---|
| Filmes | `gunicorn -w 1 -b 0.0.0.0:$PORT servico_filmes.app:app` |
| Salas | `gunicorn -w 1 -b 0.0.0.0:$PORT servico_salas.app:app` |
| Sessões | `gunicorn -w 1 -b 0.0.0.0:$PORT servico_sessoes.app:app` |
| Vendas | `gunicorn -w 1 -b 0.0.0.0:$PORT servico_vendas.app:app` |

Nas variáveis de ambiente do **serviço Sessões** defina `FILMES_URL=https://<sua-url-filmes>` e `SALAS_URL=https://<sua-url-salas>`. No serviço **Vendas** defina `SESSOES_URL=https://<sua-url-sessoes>`. Pode aumentar `HTTP_TIMEOUT_SECONDS` (por exemplo para `90`) por causa da hibernação inicial de serviços gratuitos; na demonstração é melhor acessar as quatro rotas `/health` antes dos POST.

**Atenção ao SQLite no Render gratuito:** o disco pode ser efêmero e os dados podem desaparecer quando o serviço reiniciar. Para avaliação, rode `scripts/popular_demo.py` após subir os serviços e mantenha um roteiro de cadastro demonstrativo. O projeto **não é adequado a produção com dados persistentes no plano gratuito**.

## 8. Entrega solicitada

- [ ] Subir o código para um repositório GitHub público ou compartilhado com a professora.
- [ ] Informar os quatro integrantes e suas contribuições.
- [ ] Garantir que as três integrações HTTP sejam demonstradas pelo REST Client e logs dos serviços.
- [ ] Manter no GitHub os arquivos `.http` de `rest-client/` com as requisições da demonstração.
- [ ] Publicar os quatro serviços e testar as URLs públicas.
- [ ] Entregar link do GitHub e ZIP dos fontes no portal até **27/11/2026 às 23:59**.

## 9. Arquivos principais

```text
cinema-microsservicos-python/
├── comum/
│   ├── api.py
│   └── cliente_http.py
├── servico_filmes/           # 5001 / filmes.db
│   ├── app.py
│   ├── models.py
│   ├── regras.py
│   └── rotas.py
├── servico_salas/            # 5002 / salas.db
│   ├── app.py
│   ├── models.py
│   ├── regras.py
│   └── rotas.py
├── servico_sessoes/          # 5003 / sessoes.db
│   ├── app.py
│   ├── models.py
│   ├── regras.py
│   ├── rotas.py
│   ├── filmes_helper.py
│   └── salas_helper.py
├── servico_vendas/           # 5004 / vendas.db
│   ├── app.py
│   ├── models.py
│   ├── regras.py
│   ├── rotas.py
│   └── sessoes_helper.py
├── rest-client/
│   ├── filmes.http
│   ├── salas.http
│   ├── sessoes.http
│   ├── vendas.http
│   └── integracoes.http
├── scripts/
├── tests/
├── requirements.txt
├── configuracao.env.exemplo
└── README.md
```

**Origem:** adaptado das entidades Java `Filme`, `Sala`, `Sessao`, `Pedido`, `Ingresso`, das regras em `SessaoService`, `PedidoService`, `IngressoService` e do roteiro `Projeto: arquitetura em microsserviços` fornecido pela disciplina.
