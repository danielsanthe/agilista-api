"""
Arquivo de conexão com o banco de dados AgiLista.

Responsável por:
- Configurar a conexão com o banco de dados.
- Criar o mecanismo de conexão (engine).
- Disponibilizar sessões para executar operações no banco.
"""

# Importa os recursos necessários do SQLModel.
from sqlmodel import SQLModel, create_engine, Session

# Importa as configurações centralizadas da aplicação.
from app.config import settings
from sqlalchemy import event


# ---------------------------------------------------------
# CONFIGURAÇÕES DE CONEXÃO
# ---------------------------------------------------------

# Inicializa um dicionário vazio para armazenar
# configurações adicionais da conexão.
connect_args = {}

# Verifica se o banco configurado é SQLite.
if settings.DATABASE_URL.startswith("sqlite"):

    # Permite que o SQLite seja utilizado em diferentes threads.
    # Essa configuração é necessária para seu uso com FastAPI.
    connect_args = {"check_same_thread": False}


# ---------------------------------------------------------
# CRIAÇÃO DO ENGINE
# ---------------------------------------------------------

# Cria o mecanismo responsável por gerenciar as conexões
# entre a aplicação e o banco de dados.
engine = create_engine(
    settings.DATABASE_URL,

    # Exibe no terminal os comandos SQL executados.
    # Útil durante o desenvolvimento e aprendizado.
    echo=settings.DEBUG,

    # Aplica as configurações adicionais da conexão.
    connect_args=connect_args,
)


# ---------------------------------------------------------
# ATIVAÇÃO DAS CHAVES ESTRANGEIRAS NO SQLITE
# ---------------------------------------------------------

# O SQLite precisa ativar explicitamente a verificação
# das chaves estrangeiras em cada conexão.
if settings.DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def ativar_chaves_estrangeiras(dbapi_connection, connection_record):

        cursor = dbapi_connection.cursor()

        # Ativa a integridade referencial do banco.
        cursor.execute("PRAGMA foreign_keys=ON")

        cursor.close()


def criar_tabelas() -> None:
    """
    Garante a criação das tabelas caso ainda não existam.
    Em produção com PostgreSQL/Render, as alterações de esquema são
    gerenciadas pelo Alembic (alembic upgrade head).
    """
    SQLModel.metadata.create_all(engine)        


# ---------------------------------------------------------
# DISPONIBILIZAÇÃO DE SESSÕES
# ---------------------------------------------------------

# Função responsável por fornecer uma sessão do banco
# para os endpoints e demais operações da aplicação.
def get_session():

    # Abre uma sessão utilizando o engine configurado.
    # O bloco with garante o fechamento da sessão ao terminar.
    with Session(engine) as session:

        # Disponibiliza a sessão para quem chamou a função.
        yield session