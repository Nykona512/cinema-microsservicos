# Sistema de Ingressos de Cinema — Python e microsserviços

Adaptação do projeto Java/Spring Boot `projeto-entretenimento-cultura` para a avaliação de **Sistemas Distribuídos (SATC)**. A API utiliza **Python, Flask, Flask-SQLAlchemy, SQLite, JSON e requests**, com quatro microsserviços REST independentes. Foi preparada para execução local, testes automatizados e implantação no Render.

## Aplicação publicada (Render)

| Microsserviço | URL pública | Verificar disponibilidade |
|---|---|---|
| **Filmes** | https://cinema-filmes.onrender.com | [GET /health](https://cinema-filmes.onrender.com/health) |
| **Salas** | https://cinema-salas.onrender.com | [GET /health](https://cinema-salas.onrender.com/health) |
| **Sessões** | https://cinema-sessoes.onrender.com | [GET /health](https://cinema-sessoes.onrender.com/health) |
| **Vendas** | https://cinema-vendas.onrender.com | [GET /health](https://cinema-vendas.onrender.com/health) |

As URLs acima são as informadas pela equipe após os quatro deploys. A execução de `/health` verifica a disponibilidade de cada API; a validação completa também requer testar as integrações com cadastros e compras (seção 7).

> **Observação:** acessar a raiz `/` pode retornar `404 Not Found`, pois a API expõe rotas específicas como `/health`, `/filmes`, `/salas`, `/sessoes` e `/pedidos`.

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

### Equipe e responsabilidades

| Integrante | Responsabilidade principal |
|---|---|
| **[Nome 1]** | Microsserviço Filmes |
| **[Nome 2]** | Microsserviço Salas |
| **[Nome 3]** | Microsserviço Sessões |
| **[Nome 4]** | Microsserviço Vendas |

*Substituir os nomes entre colchetes antes de entregar. Os testes, a documentação e a integração entre serviços são responsabilidades compartilhadas.*

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

## 3. Como executar no VS Code (Windows / CMD)

**Pré-requisitos:** Python 3.10+ (recomendado 3.12), VS Code, extensão REST Client e internet apenas para instalar os pacotes. Os comandos a seguir usam o **Prompt de Comando (CMD)**, sem depender do PowerShell.

Na **raiz do projeto**, crie e ative o ambiente virtual e instale as dependências:

```bat
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

Se a política do computador impedir a ativação de scripts, **não é necessário ativar o ambiente**. Instale os pacotes diretamente pelo executável do ambiente virtual:

```bat
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Abra **quatro terminais CMD** no VS Code, todos na raiz do projeto. Execute **um comando em cada terminal**:

```bat
python -m servico_filmes.app
```

```bat
python -m servico_salas.app
```

```bat
python -m servico_sessoes.app
```

```bat
python -m servico_vendas.app
```

Se não ativou o ambiente, substitua `python` por `.venv\Scripts\python.exe` nesses quatro comandos. O serviço deve ser iniciado **da raiz do repositório** para que as importações funcionem.

**Endpoints locais de saúde:**

- http://127.0.0.1:5001/health (Filmes)
- http://127.0.0.1:5002/health (Salas)
- http://127.0.0.1:5003/health (Sessões)
- http://127.0.0.1:5004/health (Vendas)

Cada microsserviço cria automaticamente seu próprio arquivo `.db` na primeira execução. Se for necessário limpar dados locais, encerre os servidores antes de excluir esses arquivos. **Não envie `.venv/` nem arquivos `.db` ao GitHub**; ambos estão incluídos no `.gitignore`.

## 4. Demonstração completa no REST Client (VS Code)

Instale a extensão **REST Client** (autor: Huachao Mao, ID `humao.rest-client`) no VS Code. Com os quatro serviços iniciados, abra os arquivos da pasta `rest-client/` e clique em **Send Request** acima da requisição desejada. Cada requisição `.http` traz a URL, o método e, quando necessário, o corpo JSON. Não há importação de coleção.

- `rest-client/filmes.http`: cadastro e consultas de filmes.
- `rest-client/salas.http`: cadastro e consultas de salas.
- `rest-client/sessoes.http`: cadastro e consultas de sessões.
- `rest-client/vendas.http`: compras, pedidos e ingressos.
- `rest-client/integracoes.http`: consultas GET entre serviços, compra que dispara POST e testes de falha.

**Ordem sugerida:** cadastrar filme → cadastrar sala → criar sessão → consultar vagas → fazer compra → consultar vagas novamente. Os IDs `1` nos arquivos partem de bancos vazios; caso necessário, substitua-os pelos valores retornados nos cadastros. Para executar contra o Render, altere as variáveis `@...Url` no início **de cada arquivo `.http` utilizado**, conforme o exemplo da seção 7.

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

```bat
python -m pytest -v tests/
```

Os testes iniciam instâncias isoladas dos quatro serviços em portas livres e com quatro bancos SQLite temporários. Verificam compra normal, cota de meia-entrada, limite R3, conflito R2, integridade entre serviços e idempotência da reserva.

## 7. Publicação e demonstração no Render

Os **quatro Web Services** utilizam o **mesmo repositório GitHub** e o mesmo `requirements.txt`, com `Root Directory` em branco (raiz do repositório). Build Command: `pip install -r requirements.txt`.

| Web Service | URL pública | Start Command |
|---|---|---|
| Filmes | https://cinema-filmes.onrender.com | `gunicorn -w 1 -b 0.0.0.0:$PORT servico_filmes.app:app` |
| Salas | https://cinema-salas.onrender.com | `gunicorn -w 1 -b 0.0.0.0:$PORT servico_salas.app:app` |
| Sessões | https://cinema-sessoes.onrender.com | `gunicorn -w 1 -b 0.0.0.0:$PORT servico_sessoes.app:app` |
| Vendas | https://cinema-vendas.onrender.com | `gunicorn -w 1 -b 0.0.0.0:$PORT servico_vendas.app:app` |

### Variáveis de ambiente necessárias

**No serviço Sessões:**

```dotenv
FILMES_URL=https://cinema-filmes.onrender.com
SALAS_URL=https://cinema-salas.onrender.com
HTTP_TIMEOUT_SECONDS=90
CINEMA_TIMEZONE=America/Sao_Paulo
```

**No serviço Vendas:**

```dotenv
SESSOES_URL=https://cinema-sessoes.onrender.com
HTTP_TIMEOUT_SECONDS=90
CINEMA_TIMEZONE=America/Sao_Paulo
```

Nos serviços Filmes e Salas, a variável `CINEMA_TIMEZONE=America/Sao_Paulo` pode ser mantida para padronização. `HTTP_TIMEOUT_SECONDS=90` é uma escolha para tolerar a ativação inicial dos serviços gratuitos que estiverem hibernando; em produção deve-se adotar prazos e mecanismos de retry adequados. **Não use `localhost` nas variáveis de integração do Render.**

### Testar as APIs públicas pelo REST Client

Nos arquivos `.http` de `rest-client/`, substitua os valores das variáveis do começo pelo bloco abaixo (sem adicionar `/health` ao final):

```http
@filmesUrl = https://cinema-filmes.onrender.com
@salasUrl = https://cinema-salas.onrender.com
@sessoesUrl = https://cinema-sessoes.onrender.com
@vendasUrl = https://cinema-vendas.onrender.com
```

**Roteiro de demonstração online:**

1. Acessar os quatro endpoints `/health` para ativar/verificar as aplicações hospedadas.
2. Enviar `POST {{filmesUrl}}/filmes` em `filmes.http` e anotar o `id` retornado.
3. Enviar `POST {{salasUrl}}/salas` em `salas.http` e anotar o `id` retornado.
4. Enviar `POST {{sessoesUrl}}/sessoes` em `sessoes.http`, utilizando os IDs corretos. Essa operação dispara **dois GET de Sessões para Filmes e Salas**.
5. Enviar `GET {{sessoesUrl}}/sessoes/{id}` para verificar a disponibilidade antes da compra.
6. Enviar `POST {{vendasUrl}}/pedidos` em `vendas.http`, utilizando o ID da sessão criada. Vendas chama Sessões por **POST para reservar vagas**.
7. Repetir `GET {{sessoesUrl}}/sessoes/{id}` e demonstrar a diminuição de `vagasDisponiveis` (exemplo: de **20 para 18** após compra de dois ingressos).
8. Exibir, se possível, os **logs de Sessões** e **Vendas** no Render para evidenciar as chamadas entre APIs.

**Importante:** consultar `/filmes/1` ou `/salas/1` diretamente pelo REST Client é útil para inspeção, mas **não substitui a demonstração da integração**. As duas chamadas GET exigidas são feitas **pelo microsserviço Sessões ao criar uma sessão**.

### Limitação do plano gratuito

Em instâncias gratuitas do Render, as aplicações podem hibernar depois de ficarem sem tráfego. O armazenamento local pode ser **efêmero**: os bancos SQLite criados no contêiner podem ser perdidos após hibernação, reinicialização ou novo deploy. Portanto, antes de uma demonstração, prepare novamente os cadastros na ordem indicada. A solução atende ao **escopo acadêmico** solicitado, mas não é indicada para produção com dados persistentes nessa modalidade de hospedagem.

**Popular dados automaticamente:** o script `scripts/popular_demo.py` usa as variáveis `FILMES_URL`, `SALAS_URL`, `SESSOES_URL` e `VENDAS_URL`; por padrão, aponta para `127.0.0.1`. Para popular o Render, configure todas essas variáveis no terminal local antes de executá-lo. Em caso de dúvida, prefira a sequência manual pelos arquivos `.http`, pois ela também serve como evidência de avaliação.

## 8. Entrega solicitada

- [ ] Subir o código para um repositório GitHub público ou compartilhado com a professora.
- [ ] Informar os quatro integrantes e suas contribuições.
- [ ] Garantir que as três integrações HTTP sejam demonstradas pelo REST Client e logs dos serviços.
- [ ] Manter no GitHub os arquivos `.http` de `rest-client/` com as requisições da demonstração.
- [x] Publicar os quatro serviços no Render (deploys informados como concluídos).
- [ ] Testar as integrações ponta a ponta nas URLs públicas.
- [ ] Confirmar com a professora a aceitação dos arquivos `.http` como evidência em vez da coleção exportada do Thunder Client (recomendada no roteiro).
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
