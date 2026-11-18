"""
Modelo de Preço por Estabelecimento do AgiLista.

Armazena registros de preços informados pelos usuários
para permitir consultas e comparações de preços por região.
"""

from typing import Optional
from sqlmodel import SQLModel, Field


class PrecoEstabelecimento(SQLModel, table=True):

    # Nome da tabela no banco de dados.
    __tablename__ = "precos_estabelecimentos"

    # Identificador único do registro de preço.
    id_preco: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    # Referência ao produto do catálogo global.
    # Permite comparar o mesmo produto entre estabelecimentos.
    produto_global_id: int = Field(
        foreign_key="produtos_globais.id_produto_global",
        index=True
    )

    # Usuário que informou o preço.
    # Preserva a origem da informação.
    usuario_id: int = Field(
        foreign_key="usuarios.id_usuario",
        index=True
    )

    # Nome do estabelecimento onde o preço foi encontrado.
    estabelecimento_nome: str = Field(max_length=150)

    # Localização do estabelecimento.
    bairro: Optional[str] = Field(default=None, max_length=100)
    cidade: str = Field(max_length=100)
    uf: str = Field(max_length=2)

    # Preço unitário informado pelo usuário.
    preco_unitario: float

    # Data e hora em que o preço foi registrado.
    data_registro: str