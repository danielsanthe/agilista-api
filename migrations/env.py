"""
Configuração do ambiente de migrações do Alembic.

Este arquivo conecta o Alembic às configurações do AgiLista
e permite identificar as tabelas definidas nos modelos SQLModel.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import event

from alembic import context

# Importa a configuração centralizada da aplicação.
from app.config import settings

# Importa todos os modelos para registrar suas tabelas
# nos metadados do SQLModel.
# Importa explicitamente todos os modelos do projeto.
from app.models import (
    Usuario,
    Categoria,
    ProdutoGlobal,
    ProdutoUsuario,
    Lista,
    ItemLista,
    PrecoEstabelecimento,
)

# Importa a estrutura de metadados do SQLModel.
from sqlmodel import SQLModel

# Obtém as configurações do arquivo alembic.ini.
config = context.config

# Configura os registros de log do Alembic.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Informa ao Alembic qual estrutura de tabelas deve ser analisada.
target_metadata = SQLModel.metadata
print("Tabelas carregadas:", list(target_metadata.tables.keys())) # remover essa linha depois dos testes.

# Obtém a URL do banco de dados definida no arquivo .env.
config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL.replace("%", "%%")
)


def run_migrations_offline() -> None:
    """
    Executa as migrações sem estabelecer uma conexão direta
    com o banco de dados.
    """

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Executa as migrações utilizando uma conexão ativa
    com o banco de dados.
    """

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Ativa as chaves estrangeiras somente quando o banco for SQLite.
    if settings.DATABASE_URL.startswith("sqlite"):

        @event.listens_for(connectable, "connect")
        def ativar_chaves_estrangeiras(dbapi_connection, connection_record):

            cursor = dbapi_connection.cursor()

            # Ativa a integridade referencial do SQLite.
            cursor.execute("PRAGMA foreign_keys=ON")

            cursor.close()

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# Define qual modo de execução será utilizado.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()