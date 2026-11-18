# AgiLista API

**API RESTful do Sistema AgiLista — Seu assistente de compras.**

A AgiLista API é o backend responsável pelo gerenciamento de dados e pelas operações do sistema AgiLista, uma solução voltada ao planejamento e controle de listas de compras, acompanhamento de gastos e organização do histórico de compras.

O projeto está sendo desenvolvido como parte do Projeto Integrador do curso Técnico em Desenvolvimento de Sistemas do IFPI.

## Objetivo

Disponibilizar os serviços de backend do AgiLista para realizar o cadastro e a autenticação de usuários, o gerenciamento de categorias e produtos, a criação e o gerenciamento de listas de compras e seus respectivos itens, além do controle dos dados relacionados às compras. A API utiliza banco de dados SQLite e disponibiliza endpoints para consulta e manipulação dessas informações.

---

## Contexto Acadêmico e Equipe

Projeto desenvolvido no **Instituto Federal de Educação, Ciência e Tecnologia do Piauí (IFPI)** — Curso **Técnico em Desenvolvimento de Sistemas**, integrando as disciplinas:

- **Projeto Integrador** — Prof. Adalto Sena
- **Programação Web Back-end** — Prof. Rogério Silva
- **Programação para Dispositivos Móveis** — Prof. Ótilio Paulo

### Equipe — Grupo ÁgiLista
- **Daniel Santos**
- **André Ferreira**
- **Rodrigo Fernandes**
- **Maria Luiza**

---

## Tecnologias utilizadas

- **Python 3.12+:** linguagem principal do backend.
- **FastAPI:** framework web assíncrono para construção da API REST e documentação OpenAPI.
- **SQLModel & SQLAlchemy:** modelagem ORM e manipulação relacional de dados.
- **PostgreSQL (Produção / Render) & SQLite (Desenvolvimento):** suporte híbrido de banco de dados configurado via variáveis de ambiente.
- **Alembic:** versionamento e execução automatizada de migrações de esquema.
- **JWT (`python-jose`) & `bcrypt`:** autenticação stateless com tokens de acesso/renovação e hash seguro de senhas.
- **Pydantic & `pydantic-settings`:** validação de contratos de entrada/saída e configuração *Twelve-Factor App*.

## Funcionalidades

O backend contempla os seguintes módulos:

- **Autenticação:** login, renovação de tokens e identificação do usuário autenticado.
- **Usuários:** estrutura de identificação e controle de acesso.
- **Categorias:** gerenciamento das categorias de produtos.
- **Produtos globais:** catálogo compartilhado de produtos identificados por código de barras.
- **Produtos do usuário:** gerenciamento dos produtos cadastrados pelos usuários.
- **Listas de compras:** criação, gerenciamento e controle dos estados das listas.
- **Itens das listas:** gerenciamento de produtos, quantidades, preços e valores de compra.
- **Preços:** estrutura prevista para o histórico de preços por estabelecimento.

## Estrutura do projeto

```text
agilista-api/
│
├── app/
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   ├── security.py
│   └── main.py
│
├── frontend/
│
├── migrations/
│   └── versions/
│
├── .env.example
├── .gitignore
├── alembic.ini
├── criar_admin.py
├── main.py
└── requirements.txt
```

## Instalação e execução local

### 1. Clonar o repositório

```bash

git clone [https://github.com/danielsanthe/agilista-api.git](https://github.com/danielsanthe/agilista-api.git)

```

### 2. Entrar na pasta do projeto

```bash
cd agilista-api
```

### 3. Criar o ambiente virtual

```bash
python -m venv .venv
```

### 4. Ativar o ambiente virtual

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux:**

```bash
source .venv/bin/activate
```

### 5. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 6. Configurar as variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto, utilizando como referência as configurações de `app/config.py`.

Exemplo:

```env
DATABASE_URL=sqlite:///./agilista.db
APP_NAME=AgiLista API
ENVIRONMENT=development
DEBUG=true
JWT_SECRET_KEY=INSIRA_UMA_CHAVE_SEGURA
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Importante:** não compartilhe nem envie o arquivo `.env` ao GitHub.

### 7. Executar as migrações

```bash
python -m alembic upgrade head
```

As alterações na estrutura do banco de dados são gerenciadas pelo Alembic.

### 8. Iniciar a API

```bash
fastapi dev main.py
```

## Documentação da API

Com a aplicação em execução, a documentação interativa pode ser acessada pelo Swagger:

```text
http://127.0.0.1:8000/docs
```

Documentação alternativa ReDoc:

```text
http://127.0.0.1:8000/redoc
```

## Autenticação

A API utiliza autenticação baseada em JWT (JSON Web Token).

As principais operações de autenticação são:

| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/api/v1/auth/signin` | Autenticar usuário |
| POST | `/api/v1/auth/refresh` | Renovar tokens |
| GET | `/api/v1/auth/me` | Consultar usuário autenticado |

As rotas protegidas utilizam o cabeçalho:

```text
Authorization: Bearer SEU_ACCESS_TOKEN
```

As permissões administrativas são verificadas pelo tipo de usuário autenticado.

## Publicação

A API está sendo preparada para publicação no Render, inicialmente com o objetivo de disponibilizar sua documentação Swagger para acesso externo.

A integração com o aplicativo AgiLista Mobile será realizada em uma etapa posterior.

## Estado do desenvolvimento

**Em desenvolvimento.**

O projeto está sendo implementado de forma modular, com separação entre modelos, schemas, rotas, dependências e serviços.

## Projeto acadêmico

**Instituição:** Instituto Federal do Piauí — IFPI  
**Curso:** Técnico em Desenvolvimento de Sistemas  
**Projeto:** AgiLista — Seu assistente de compras.

---

**AgiLista — Planeje. Compre. Controle.**