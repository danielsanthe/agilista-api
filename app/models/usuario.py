
"""
Modelo de Usuário do AgiLista.

Representa os usuários cadastrados na aplicação.

Responsabilidades:
- Armazenar os dados pessoais do usuário.
- Armazenar os dados de acesso.
- Controlar o plano contratado.
- Controlar o perfil de acesso ao sistema.
- Registrar informações de sincronização.
"""

# Importa os recursos necessários do SQLModel.
from typing import Optional
from sqlmodel import SQLModel, Field


# ---------------------------------------------------------
# MODELO DA TABELA USUARIOS
# ---------------------------------------------------------

class Usuario(SQLModel, table=True):

    # Define o nome da tabela no banco de dados.
    __tablename__ = "usuarios"

    # Identificador principal do usuário no servidor.
    id_usuario: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    # Identificador utilizado para relacionar o registro
    # do servidor com o banco SQLite do dispositivo.
    servidor_id: Optional[int] = Field(default=None)

    # Nome completo do usuário.
    nome_usuario: str = Field(max_length=150)

    # E-mail utilizado para identificação e login.
    email: str = Field(
        index=True,
        unique=True,
        max_length=150
    )

    # CPF do usuário.
    cpf: Optional[str] = Field(default=None, max_length=14)

    # Telefone de contato.
    telefone: Optional[str] = Field(default=None, max_length=20)

    # CEP do endereço.
    cep: Optional[str] = Field(default=None, max_length=10)

    # Logradouro do endereço.
    logradouro: Optional[str] = Field(default=None, max_length=200)

    # Número do endereço.
    numero: Optional[str] = Field(default=None, max_length=20)

    # Bairro do endereço.
    bairro: Optional[str] = Field(default=None, max_length=100)

    # Cidade do usuário.
    cidade: Optional[str] = Field(default=None, max_length=100)

    # Unidade federativa.
    uf: Optional[str] = Field(default=None, max_length=2)

    # Senha armazenada em formato de hash.
    # Nunca devemos armazenar a senha original.
    senha_hash: str

    # Plano atual do usuário.
    # Controla a modalidade de utilização do aplicativo.
    # Plano atual do usuário (None para ADMIN; "FreeTrial" padrão para CLIENTE).
    tipo_plano: Optional[str] = Field(
        default="FreeTrial",
        max_length=30
    )

    # Perfil de acesso do usuário.
    # COMUM: acesso às funcionalidades normais.
    # ADMIN: acesso administrativo ao sistema.
    # Não confundir com tipo_plano.
    tipo_usuario: str = Field(
        default="CLIENTE",
        max_length=20
    )

    # Indica se o registro foi sincronizado.
    # No servidor, esse campo representa o controle
    # recebido do aplicativo e não substitui o servidor_id.
    flag_sincronizado: int = Field(default=0)

    # Data de cadastro do usuário.
    data_cadastro: str

    # Data da última sincronização.
    ultima_sincronizacao: Optional[str] = Field(default=None)
