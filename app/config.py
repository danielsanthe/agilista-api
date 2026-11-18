"""
Arquivo de configurações da aplicação AgiLista.

Responsável por:
- Definir o endereço de conexão com o banco de dados.
- Configurar os parâmetros de autenticação JWT.
- Carregar configurações externas do arquivo .env.
"""

# Importa BaseSettings para gerenciar as configurações da aplicação.
# SettingsConfigDict permite configurar a leitura do arquivo .env.
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------
# CLASSE DE CONFIGURAÇÕES
# ---------------------------------------------------------

# A classe Settings centraliza as configurações do sistema.
# Herda de BaseSettings para permitir a leitura de variáveis
# definidas no ambiente ou no arquivo .env.
class Settings(BaseSettings):

    # Endereço de conexão com o banco de dados.
    # Nome da aplicação exibido na documentação Swagger
    APP_NAME: str = "AgiLista API"

    # Ambiente de execução (development, production, testing)
    ENVIRONMENT: str = "development"

    # Habilita mensagens detalhadas de log SQL e depuração
    DEBUG: bool = True

    # Endereço de conexão com o banco de dados (SQLite local ou PostgreSQL no Render/Supabase)
    DATABASE_URL: str = "sqlite:///./agilista.db"

    # Chave secreta utilizada para assinar os tokens JWT.
    # Em produção, deve ser substituída por uma chave forte
    # armazenada em uma variável de ambiente.
    JWT_SECRET_KEY: str = "troque-esta-chave-por-uma-chave-segura"

    # Algoritmo utilizado para assinar os tokens de autenticação.
    JWT_ALGORITHM: str = "HS256"

    # Tempo de validade do token de acesso, em minutos.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalizar_database_url(cls, v: str) -> str:
        """
        Ajusta prefixos postgres:// ou postgresql:// (padrão Render/Supabase)
        para o dialeto postgresql+psycopg:// usado pelo SQLAlchemy com psycopg3.
        """
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+psycopg://", 1)
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v

    # Configura a leitura das variáveis externas.
    model_config = SettingsConfigDict(
        env_file=".env",           # Arquivo que contém as configurações.
        env_file_encoding="utf-8",  # Codificação utilizada na leitura.
        extra="ignore",
    )


# ---------------------------------------------------------
# INSTÂNCIA DAS CONFIGURAÇÕES
# ---------------------------------------------------------

# Cria um objeto da classe Settings.
# A partir dele, os demais arquivos podem acessar as configurações.
settings = Settings()