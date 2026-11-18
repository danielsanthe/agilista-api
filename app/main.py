"""
=============================================================================
AGILISTA API — PONTO DE ENTRADA PRINCIPAL (MAIN)
=============================================================================

Arquivo responsável por:
- Inicializar a aplicação FastAPI.
- Definir os metadados e a documentação Swagger / ReDoc.
- Configurar o Middleware de CORS para requisições web.
- Gerenciar o ciclo de vida da API (Lifespan) e carga inicial.
- Montar os arquivos estáticos do Painel Web (HTML/JS Pub-Sub).
- Executar a carga inicial de categorias padrão no servidor.
- Registrar os roteadores modulares (APIRouter) devidamente padronizados.
- Disponibilizar rotas de monitoramento e verificação de saúde.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

# Configurações e conexão com o banco de dados do servidor.
from app.config import settings
from app.database import engine

# Serviço responsável pela carga inicial de categorias padrão.
from app.services.carga_inicial import cadastrar_categorias_padrao

# Importação dos roteadores modulares padronizados
from app.routers import (
    auth,
    categorias,
    itens_lista,
    listas,
    produtos_globais,
    produtos_usuario,
    usuarios,
)


# =====================================================================
# SEÇÃO 1: CICLO DE VIDA DA APLICAÇÃO (LIFESPAN)
# =====================================================================
@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """
    Gerencia a inicialização e o encerramento da API no servidor.

    Executa a verificação e o cadastro inicial das categorias padrão no banco.
    Nota: As tabelas e migrações de esquema são gerenciadas pelo Alembic/SQLModel.
    """
    # Abre uma sessão com o banco de dados do servidor
    with Session(engine) as session:
        # Cadastra as categorias padrão, caso ainda não existam no banco
        cadastrar_categorias_padrao(session)

    # Libera a aplicação para receber requisições do aplicativo mobile e web
    yield

    # Espaço reservado para procedimentos de encerramento de conexões/recursos


# =====================================================================
# SEÇÃO 2: INSTÂNCIA PRINCIPAL DA APLICAÇÃO FASTAPI
# =====================================================================
app = FastAPI(
    title="AgiLista API",
    description=(
        "API RESTful do AgiLista, responsável pelo gerenciamento e pela "
        "sincronização de dados entre o aplicativo mobile e o banco de "
        "dados do servidor, incluindo usuários, produtos, categorias, "
        "listas de compras e histórico de preços."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=ciclo_de_vida,
)


# =====================================================================
# SEÇÃO 3: MIDDLEWARE DE CORS (CROSS-ORIGIN RESOURCE SHARING)
# =====================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================================
# SEÇÃO 4: REGISTRO DE ROTAS MODULARES (APIRouter)
# =====================================================================
app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(categorias.router)
app.include_router(produtos_usuario.router)
app.include_router(produtos_globais.router)
app.include_router(listas.router)
app.include_router(itens_lista.router)

# Roteadores planejados para expansão futura (ex: monitoramento de preços):
# from app.routers import precos
# app.include_router(precos.router)


# =====================================================================
# SEÇÃO 5: MONTAGEM DO FRONT-END WEB ESTÁTICO (VANILLA JS / PUB-SUB)
# =====================================================================
if os.path.isdir("frontend"):
    app.mount(
        "/frontend",
        StaticFiles(directory="frontend", html=True),
        name="frontend"
    )


# =====================================================================
# SEÇÃO 6: ENDPOINTS DE INFORMAÇÕES E MONITORAMENTO DO SISTEMA
# =====================================================================
@app.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Status da API",
    description="Apresenta informações detalhadas sobre o estado operacional do servidor AgiLista.",
    tags=["Monitoramento"],
    responses={
        200: {
            "description": "Informações de status do servidor retornadas com sucesso."
        }
    }
)
def inicio():
    """
    Retorna o status operacional da API e os links de acesso às documentações e ao painel web.
    """
    return {
        "sistema": "AgiLista API",
        "versao": "1.0.0",
        "status": "online",
        "docs_swagger": "/docs",
        "docs_redoc": "/redoc",
        "painel_web": "/frontend/",
    }


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Verificação de Saúde (Health Check)",
    description="Endpoint utilizado por serviços de hospedagem (Render, Docker, AWS) para checagem de integridade.",
    tags=["Monitoramento"],
    responses={
        200: {
            "description": "Aplicação saudável e operacional."
        }
    }
)
def verificar_saude():
    """
    Retorna a confirmação de que a aplicação está no ar e pronta para receber tráfego.
    """
    return {
        "status": "ok",
        "ambiente": getattr(settings, "ENVIRONMENT", "desenvolvimento"),
    }